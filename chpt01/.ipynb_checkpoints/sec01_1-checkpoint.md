## 1.1. Método de coleta das informações

<div style="text-align: justify"> Neste relatório, foram utilizadas quatro fontes principais de informações para a obtenção dos dados de monitoramento da qualidade do ar no Brasil: Consulta 2025, MonitorAr, Coleta Interna e PurpleAir. A coleta de informações foi realizada através de pesquisa nos endereços eletrônicos dos OEMAs (Orgãos Estaduais de Meio Ambiente), com o objetivo de verificar a disponibilidade de informações referentes à qualidade do ar, as características da rede de monitoramento e a publicação de dados, relatórios e planos. Também foram realizadas buscas pela equipe deste relatório em plataformas de dados de monitoramento para a complementação de informações.</div><br/>

```{warning}
As informações obtidas por meio do questionário foram compiladas e, em alguns casos, complementadas com os dados disponíveis no Sistema Nacional de Gestão da Qualidade do Ar (MonitorAr), dados da plataforma de qualidade do ar do Instituto de Energia e Meio Ambiente - IEMA e coleta manual realizada pela equipe do projeto. 

```

<div style="text-align: justify"> Um formulário foi enviado às unidades federativas solicitando os dados de monitoramento, informações sobre as redes estaduais e outros aspectos relacionados à qualidade do ar. Os dados recebidos diretamente por meio desse formulário foram classificados como provenientes da Consulta 2025. O formulário visou agregar as seguintes informações:
    <ul>
      <li>características da rede de monitoramento no estado, se houver;</li>
      <li>modo de divulgação de dados de qualidade do ar, se houver;</li>
      <li>interligação com o Sistema MonitorAr;</li>
      <li>disponibilização dos dados de qualidade do ar;</li>
      <li>elaboração e divulgação de Relatório de Avaliação de Qualidade do Ar;</li>
      <li>elaboração e aplicação de Plano de Controle de Emissões Atmosféricas;</li>
      <li>elaboração e disponibilização de Inventário de Emissões Atmosféricas.</li>
      <li>INCLUIR MAIS COISAS.</li>        
    </ul>
</div>    

```{note}
O questionário foi preenchido por todos os OEMAs das UFs do Brasil, atingindo uma taxa de retorno de 100%.

```

<div style="text-align: justify">Alguns estados informaram que seus dados estão integrados ao sistema MonitorAr, enquanto outros indicaram o uso de plataformas próprias de monitoramento.Nestes últimos casos, a equipe deste relatório realizou a extração direta dos dados, categorizada como Coleta Interna.
<br>
Os estados da Bahia (BA) e Maranhão (MA) não informaram possuir rede de monitoramento. No entanto, a equipe localizou plataformas públicas com dados disponíveis e desenvolveu rotinas automáticas de extração, acessíveis nos links abaixo e também foram classificadas como Coleta Interna:
•	webScraper_MA.py
•	webScraper_BA.py
<br>
Os estados do Rio de Janeiro (RJ) e São Paulo (SP) indicaram possuir redes próprias de monitoramento e plataformas específicas para obtenção dos dados.Para o RJ, foi desenvolvido um script de extração automática (webScraper_RJ.py) uma vez que os dados não foram enviados pela OEMA e a plataforma apresenta restrições de download. Os dados de SP foram obtidos utilizando o código desenvolvido pelo pesquisador Dr. Mario Gavidia Calderón, disponível no repositório qualR.</div>  

```{note}
Todos os códigos de extração e tratamento dos dados estão disponíveis no repositório do projeto: https://github.com/LCQAr/RQAR_2025_book
```
<div style="text-align: justify"> Por fim, foram obtidas informações sobre a rede de sensores da plataforma PurpleAir (https://www2.purpleair.com). O código para obtenção dessas informações está disponível em getPurpleAirData.ipynb.</div>  
    
```{warning}
Não foram extraídos os dados de concentração da plataforma PurpleAir, apenas as coordenadas geográficas, poluentes monitorados e as datas de início e fim de operação de cada sensor.
```



