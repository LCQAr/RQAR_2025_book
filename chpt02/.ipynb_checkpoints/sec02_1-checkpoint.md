## 2.1.	Poluentes, fontes de emissão e dispersão

* Figura ilustrando o processo de  poluição
* Figura ilustrando o processo de gestão da qualidade do ar e m qual ponto o relatório se encaixa

<!-- Load Plotly and PapaParse for CSV parsing -->
<script src="https://cdn.plot.ly/plotly-2.26.1.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js"></script>

<div>
  <label>Station:</label>
  <select id="stationSelect"></select>

  <label>Pollutant:</label>
  <select id="pollutantSelect"></select>

  <label>Start date:</label>
  <input type="datetime-local" id="startDate">

  <label>End date:</label>
  <input type="datetime-local" id="endDate">

  <button id="updateBtn">Update Plot</button>
</div>

<div id="plotDiv" style="width:100%;height:600px;"></div>

<script>
const CSV_URL = "../_static/Monitoramento_QAr_BR_teste.csv";  // caminho relativo no Jupyter Book
let rawData = [];
let stationPollutants = {};

// Carregar CSV com PapaParse
Papa.parse(CSV_URL, {
  download: true,
  header: true,
  skipEmptyLines: true,
  complete: function(results) {
    rawData = results.data.filter(r => r.ID_MMA && r.POLUENTE); // remover linhas vazias
    console.log('CSV loaded', rawData.length, 'rows');
    buildStationPollutantMap();
    populateStationSelect();
    setDefaultDates();
  },
  error: function(err) {
    console.error('CSV load error:', err);
  }
});

// Construir mapa estação -> poluentes
function buildStationPollutantMap() {
  stationPollutants = {};
  rawData.forEach(row => {
    if (!stationPollutants[row.ID_MMA]) {
      stationPollutants[row.ID_MMA] = new Set();
    }
    if(row.POLUENTE) {
      stationPollutants[row.ID_MMA].add(row.POLUENTE);
    }
  });
  for (const station in stationPollutants) {
    stationPollutants[station] = Array.from(stationPollutants[station]);
  }
}

// Popular dropdown de estações
function populateStationSelect() {
  const stationSelect = document.getElementById("stationSelect");
  stationSelect.innerHTML = "";
  Object.keys(stationPollutants).sort().forEach(station => {
    const opt = document.createElement("option");
    opt.value = station;
    opt.textContent = station;
    stationSelect.appendChild(opt);
  });
  stationSelect.addEventListener("change", populatePollutantSelect);
  populatePollutantSelect();  // inicial
}

// Popular dropdown de poluentes com base na estação
function populatePollutantSelect() {
  const station = document.getElementById("stationSelect").value;
  const pollutantSelect = document.getElementById("pollutantSelect");
  pollutantSelect.innerHTML = "";
  (stationPollutants[station] || []).forEach(pol => {
    const opt = document.createElement("option");
    opt.value = pol;
    opt.textContent = pol;
    pollutantSelect.appendChild(opt);
  });
}

// Definir valores default para os campos de data baseado no CSV carregado
function setDefaultDates() {
  let dates = rawData.map(r => {
    return new Date(r.ANO, r.MES - 1, r.DIA, r.HORA);
  }).filter(d => !isNaN(d));
  if(dates.length === 0) return;

  const minDate = new Date(Math.min(...dates));
  const maxDate = new Date(Math.max(...dates));

  // Ajustar formato para datetime-local: "YYYY-MM-DDTHH:mm"
  document.getElementById("startDate").value = minDate.toISOString().slice(0,16);
  document.getElementById("endDate").value = maxDate.toISOString().slice(0,16);
}

// Quebra os dados em segmentos sem NaN para o gráfico
function splitNaNSegments(x, y) {
  let segments = [];
  let currentX = [], currentY = [];
  for (let i = 0; i < y.length; i++) {
    if (y[i] == null || isNaN(y[i])) {
      if (currentX.length > 0) {
        segments.push({x: currentX, y: currentY});
        currentX = [];
        currentY = [];
      }
    } else {
      currentX.push(x[i]);
      currentY.push(y[i]);
    }
  }
  if (currentX.length > 0) {
    segments.push({x: currentX, y: currentY});
  }
  return segments;
}

// Atualizar gráfico ao clicar no botão
document.getElementById("updateBtn").addEventListener("click", function() {
  const station = document.getElementById("stationSelect").value;
  const pollutant = document.getElementById("pollutantSelect").value;
  const startDateVal = document.getElementById("startDate").value;
  const endDateVal = document.getElementById("endDate").value;

  const startDate = startDateVal ? new Date(startDateVal) : null;
  const endDate = endDateVal ? new Date(endDateVal) : null;

  // Filtrar e limpar dados
  const filtered = rawData.filter(row =>
    row.ID_MMA === station &&
    row.POLUENTE === pollutant
  ).map(row => {
    let dt = new Date(row.ANO, row.MES - 1, row.DIA, row.HORA);
    let val = parseFloat(String(row.VALOR).replace(",", "."));
    if (val < 0) val = null;
    return {datetime: dt, valor: val};
  }).filter(row =>
    (!startDate || row.datetime >= startDate) &&
    (!endDate || row.datetime <= endDate)
  );

  // Ordenar por data
  filtered.sort((a, b) => a.datetime - b.datetime);

  const x = filtered.map(r => r.datetime);
  const y = filtered.map(r => r.valor);

  // Criar segmentos sem NaN para plotagem
  const segments = splitNaNSegments(x, y);

  // Criar traces para o Plotly
  let traces = segments.map(seg => ({
    x: seg.x,
    y: seg.y,
    mode: "lines",
    line: {color: "black", width: 1},
    showlegend: false
  }));

  // Plotar gráfico
  Plotly.newPlot("plotDiv", traces, {
    title: `Série temporal - ${station} - ${pollutant}`,
    hovermode: "x unified",
    plot_bgcolor: "rgba(0.8,0.8,0.8,0.2)",
    yaxis: {title: "Concentração (µg/m³)"},
    xaxis: {title: "Data/Hora"}
  });
});
</script>