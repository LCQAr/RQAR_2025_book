## 1.1. Método de coleta de dados

<div style="text-align: justify"> Neste relatório, foram utilizadas quatro fontes principais de informações para a obtenção dos dados de monitoramento da qualidade do ar no Brasil: (1) Formulário para as OEMA aplicado pelo MMA (Consulta 2025); (2) Coleta de dados na plataforma MonitorAr (MonitorAr); (3) Coleta Interna em plataformas estaduais (Coleta interna); (4) Coleta de dados na plataforma PurpleAir (PurpleAir 2025). A coleta de informações foi realizada com o objetivo de verificar a disponibilidade de informações referentes à qualidade do ar, as características da rede de monitoramento e a publicação de dados, relatórios e planos. </div>

```{warning}
As informações obtidas por meio do questionário foram compiladas e, em alguns casos, complementadas com os dados disponíveis no Sistema Nacional de Gestão da Qualidade do Ar (MonitorAr), dados da plataforma de qualidade do ar do Instituto de Energia e Meio Ambiente - IEMA <cite id="b2b7k"><a href="#zotero%7C22267313%2F6DZ4YCC4">(IEMA, 2025)</a></cite> e coleta manual realizada pela equipe do projeto.
```

<div style="text-align: justify">Com o objetivo de levantar informações atualizadas, foi encaminhado um formulário às Unidades Federativas (UFs). As respostas recebidas compõem a Consulta 2025, base de referência para o diagnóstico do cenário nacional. O formulário foi estruturado em seções temáticas para que os estados pudessem detalhar as ações em andamento, como:  </div><br/>

<div style="text-align: justify"><b><li> Estrutura da rede de monitoramento:</b> identificação das estações existentes em cada UF, discriminando estações de referência, de operação própria, vinculadas a licenças ambientais e indicativas (sensores de baixo custo). Também foram solicitadas informações sobre o número de unidades, categorias, métodos utilizados e calibração dos equipamentos; <li></div><br/>

<div style="text-align: justify"><b><li> Mudanças na rede:</b> registro de alterações ocorridas em 2024, como expansão, inativação ou reativação de estações e ampliação; <li></div><br/>

<div style="text-align: justify"><b><li> Dados de monitoramento:</b> levantamento sobre o tratamento e formatação dos dados, métodos utilizados, disponibilidade pública das informações e envio dos dados de monitoramento, para construção de uma base de dados nacional de qualidade do ar; <li></div><br/>

<div style="text-align: justify"><b><li> Integração ao Sistema MonitorAr:</b> verificação do grau de integração dos dados estaduais ao sistema nacional, identificação de estações ainda não integradas, parâmetros monitorados, localização e prazos estimados para conclusão da integração; <li></div><br/>

<div style="text-align: justify"><b><li> Relatórios de Avaliação da Qualidade do Ar:</b> checagem da publicação de relatórios nos últimos quatro anos e divulgação ao público; <li></div><br/>

<div style="text-align: justify"><b><li> Planos de Controle de Emissões Atmosféricas:</b> identificação da existência de planos publicados ou em elaboração; <li></div><br/>

<div style="text-align: justify"><b><li> Inventários de Emissões Atmosféricas:</b> verificação da publicação de inventários recentes e métodos utilizados (medições, estimativas ou outros); <li></div><br/>

<div style="text-align: justify"><b><li> Planos de Gestão da Qualidade do Ar:</b> existência e estágio de execução de planos de gestão estaduais. <li></div><br/>

<div style="text-align: justify"> Além disso, foi solicitado o preenchimento detalhado das informações técnicas das estações de monitoramento em operação nas UFs. Para cada estação, os estados deveriam informar: </div><br/>
    <ul>
      <li>Identificação do município;</li>
      <li>Proprietário e operador; </li>
        <li>Operador; </li>
      <li>Tipo de funcionamento (automática ou manual)</li>
        <li>Categoria (referência ou indicativa);</li>
        <li>Status de funcionamento (ativa ou inativa);</li>
        <li>Método de amostragem;</li>
        <li>Calibração;</li>
      <li>Fabricante; </li>
         <li>Modelo; </li>
        <li>Certificação; </li>
         <li>Poluentes monitorados; </li>
      <li>Localização geográfica (latitude, longitude e elevação); </li>
        <li>Início e fim de operação; </li>
        <li>Anos monitorados;</li>
      <li>Finalidade das medições; </li>
      <li>Informações sobre integração ao MonitorAr; </li>
        <li>Realocação. </li>
    </ul>

```{note}
O questionário foi preenchido por todos os OEMA do Brasil, atingindo uma taxa de retorno de 100%.
```

<div style="text-align: justify">Algumas UFs informaram que seus dados estão integrados ao sistema MonitorAr, enquanto outros indicaram o uso de plataformas próprias de monitoramento. Nesse caso, a equipe deste relatório realizou a extração direta dos dados, as categorizando como Coleta Interna.</div><br/>

```{warning}
O nível de detalhamento das informações foi variável em função das respostas das UFs. As informações faltantes foram indicadas como **“Não Declaradas”**.
```

<div style="text-align: justify">Os estados da Bahia (BA) e Maranhão (MA) informaram não possuir rede de monitoramento. No entanto, a equipe localizou plataformas públicas com dados disponíveis e desenvolveu rotinas automáticas de extração, acessíveis nos links abaixo (coleta interna):</div>
    <ul>
      <li>webScraper_MA.py</li>
      <li>webScraper_BA.py</li>
    </ul>

<div style="text-align: justify"> Os estados do Rio de Janeiro (RJ) e São Paulo (SP) declararam que possuem plataformas específicas para obtenção dos dados. Para o RJ, foi desenvolvido um script de extração automática uma vez que, os dados não foram enviados pela OEMA e a plataforma apresenta restrições de download. Os dados de SP foram obtidos utilizando o código desenvolvido pelo pesquisador Dr. Mario Gavidia Calderón, disponível no repositório qualR (Calderón; Kamigauti, 2024).</div>

    
```{note}
Todos os códigos de extração e tratamento dos dados estão disponíveis no repositório do projeto: https://github.com/LCQAr/RQAR_2025_book.
Para a coleta dos dados do estado do RJ foi utilizado o script: https://github.com/LCQAr/RQAR_2025_book/blob/main/scripts/webScraper_RJ.py. 

```

<div style="text-align: justify"> Adicionalmente, foram obtidas informações sobre a rede de sensores da plataforma PurpleAir (https://www2.purpleair.com). As informações foram obtidas via API e o procedimento está disponível em getPurpleAirData.ipynb (https://github.com/LCQAr/RQAR_2025_book/blob/main/scripts/getPurpleAirData.ipynb).</div>
    
```{warning}
A extração dos dados da plataforma PurpleAir contemplou exclusivamente metadados das estações, com foco em: situação de funcionamento, categoria, marca e modelo, poluentes monitorados, datas de início e fim de operação, latitude e longitude, e anos monitorados.
```
