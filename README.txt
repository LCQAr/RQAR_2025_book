# Introdução

...

# Organização

...

## Importação de scripts

Adicione seu script na pasta ```scripts```. Para importar dentro do seu notebook, faça da seguinte forma:

```python
from scripts import meupacote
```

Onde "meupacote" é o nome do seu arquivo de script (algo como meupacote.py). Se quiser importar somente algo dentro do seu script (como um método ou uma classe), use a forma abaixo:

```python
from scripts.meupacote import minhafuncao
```


OBSERVAÇÃO = As figuras e tabelas que possuem numeração seguem a ordem do relatório diagramado = https://www.gov.br/mma/pt-br/centrais-de-conteudo/publicacoes/qualidade-ambiental-e-meio-ambiente-urbano/relatorio-anual-de-acompanhamento-da-qualidade-do-ar-2024.pdf


----------chpt01-----------
chpt01.md = Apresentação 

sec01_1.md = Método de coleta das informações 

sec01_2.ipynb = Origem dos dados 

    Tabela 1 – Origem das informações sobre a realização de monitoramento da qualidade do ar pelos OEMAs.

    Tabela 2 – Origem dos dados de monitoramento utilizados para avaliação da qualidade do ar no Brasil no ano de 2023.

  
----------chpt02-----------
chp02.md = Definições, padrões e parâmetros da qualidade do ar no Brasil 

sec02_1.md = Poluentes, fontes de emissão e dispersão

    Figura ilustrando o processo de  poluição

    Figura ilustrando o processo de gestão da qualidade do ar e m qual ponto o relatório se encaixa


sec02_2.md = Monitoramento da qualidade do ar

    Fotos e figuras para exemplificar

    Tabela com os métodos e referenciar guia de monitoramento


sec02_3.md = Impactos no meio ambiente causados pela poluição atmosférica

    Figuras de artigos e tabelas montadas manualmente


sec02_4.md = Padrões, classificações e metas de atendimento 

    Tabela 3 – Comparativo de padrões de qualidade do ar entre Resolução Conama no 491/2018, Resolução Conama no
        506/2024 e Valores-guia da OMS.


sec02_5.md = Governança sobre a qualidade do ar no Brasil 

    Tabela 4 – A governança da qualidade do ar no Brasil – dados de 2024. Dados coletados no formulário aplicado pelo MMA e páginas dos OEMAs.



----------chpt03-----------
chp03.md A Rede de Monitoramento Brasileira 


sec03_1.ipynb =  
        
    3.1.1. Distribuição espacial

        Figura 1 – a) Distribuição espacial das UFs no Brasil. b) Distribuição espacial das estações de monitoramento da
            qualidade do ar no Brasil por status. b) Número de estações de monitoramento ativas e inativas nas UFs do Brasil

        Tabela 5 – Número total de estações de monitoramento da qualidade do ar no Brasil.
            Dados coletados no formulário aplicado pelo MMA.


    3.1.2. Equipamentos utilizados

        Tabela 6 – Número de estações de monitoramento da qualidade do ar de referência ou equivalente no Brasil. Dados
            coletados no formulário aplicado pelo MMA.Tabela com equipamentos utilizados – total e por estados. Tabela utilizando planilha Monitoramento_QAr.csv

        Figura 2 – a) Distribuição espacial das UFs no Brasil. b) Distribuição espacial das estações de monitora-
            mento da qualidade do ar no Brasil por tipo. c) Número de estações de monitoramento de referência
            e indicativas nas UFs do Brasil.

        Figura 3 – Distribuição espacial das estações de monitoramento da qualidade do ar nas regiões do Brasil por status.
        
        Apêndice com toda a lista de equipamentos com detalhes  

        Figura exemplo com dados da rede automática. Tentar fazer dropdown menu para escolher a estação 

        Figura exemplo com dados da rede com rede manual 

        Figura exemplo com dados da rede indicativa 


    3.1.3. Poluentes monitorados

        Tabela 7 – Parâmetros da Resolução Conama n. 506/2024 monitorados por estações de referência ou equivalentes em 2024. Dados coletados no formulário aplicado pelo MMA.
        
        Figura com o número de poluentes medidos em cada estação - pintar as bolinhas. Montar um folium com os tags dos poluentes monitorados no mapa iterativo


sec03_2.ipynb = Operação e manutenção das estações e controle de qualidade 

    Texto sobre os sistemas de operação, manutenção e controle de qualidade 

    Tabela 9 – Completude média das medições de qualidade do ar (escala diária) nas UFs do Brasil no ano de 2023.


    3.2.1. Frequência de manutenção e calibração, 

        Lista por estação no apêndice 

        Figura com manutenção adequada e inadequada 

        Tabela por estado


    3.2.2. Metodologia de tratamento dos dados e controle de qualidade 

        Lista de metodologia por estações/estado 

        Figura das estações com controle e sem controle 

        Tabela por estado


sec03_3.ipynb = Finalidade do monitoramento 

    Figura com finalidade do monitoramento no espaço**

    Tabela da finalidade do monitoramento por estado**


sec03_4.ipynb = Cobertura do monitoramento da qualidade do ar 


    3.4.1. Representatividade espacial das estações

        Tabela 11 – Cobertura das redes de monitoramento da qualidade do ar no Brasil considerando a área total do país e a
            área urbana. Análise realizada utilizando dados do IBGE (IBGE, 2019; IBGE, 2022

        Tabela 12 – Cobertura das redes de monitoramento da qualidade do ar nas UFs brasileiras considerando a área total e
            urbana de cada UF. Análise realizada utilizando dados do IBGE (2019; 2022a)   

        Figura 7 – Percentual de cobertura das redes de monitoramento da qualidade do ar (ativas) nas UFs brasileiras
            considerando a área urbana. Análise realizada utilizando dados do IBGE (IBGE, 2019; IBGE, 2022a)


    3.4.2. Usos do solo monitorados 

        Figura 8 – a) Distribuição espacial das UFs no Brasil. b) Distribuição das estações de monitoramento e uso predominante
            do solo no entorno, considerando um raio de 1km. Classificação do uso do solo conforme projeto MapBiomas (2023)
        
        Tabela 14 – Número de estações e uso do solo predominante em um raio de 1 km. Classificação do uso
            do solo e dados do projeto MapBiomas (2023)

        Figura 9 –Percentual dos usos do solo em um raio de 5km ao redor das estações onde o monitoramento da qualidade
            do ar foi considerado representativo no espaço. Classificação do uso do solo conforme projeto MapBiomas (2023).


    3.4.3. Cobertura populacional 

        Tabela 13 – Estimativa da população atendida pelo monitoramento da qualidade do ar de referência (ou equivalente) e
            indicativo em cada UF. Análise realizada utilizando dados do IBGE (2019; 2022a; 2022b).



----------chpt04-----------
chpt04.md = Qualidade do Ar no Brasil 

- MODELAGEM E EMISSÕES = ANO QUE VEM


sec04_1.ipynb = Violações dos padrões de qualidade ar no Brasil 

    Tabela 10 – Ranqueamento das cinco estações com o maior número de violações dos Padrões de Qualidade do Ar de O 3, MP10, MP2,5 e SO2 no ano de 2023. 
    TENTAR FAZER UMA TABELA ITERATIVA ONDE O USUÁRIO POSSA FILTRAR AS ESTAÇÕES

    TENTAR FAZER UM DROPDOWN MENU PARA ESCOLHER QUAL SÉRIE TEMPORAL VISUALIZAR NO LIVRO. Colocar padrões da CONAMA. 


sec04_2.ipynb = Designação de áreas de atendimento e não atendimento dos padrões de qualidade do ar 

    Figura das Cidades que não atendem, atendem e não classificadas. Folium

    Figura com classificação de acordo com o atendimento de cada padrão da CONAMA. Folium

    Tabela com estatísticas acima. Tabela iterativa com filtro


sec04_3.ipynb = População exposta para cada padrão de qualidade do ar 

    Tabela com estatísticas da população exposta para cada padrão de qualidade do ar por estado

    Tabela iterativa por estação de monitoramento e cidade

    Figura com estação de monitoramento que viola cada um dos padrões. Demonstrar buffer e população atingida/setores sensitários.


sec04_4.ipynb = Análise de tendências e sazonalidade da qualidade do ar no Brasil 

    Análise de tendência por estação TABELA ITERATIVA ONDE O USUÁRIO POSSA FILTRAR AS ESTAÇÕES

    Análise de tendência por estado TABELA GERAL

    Figura com tendência por estação no mapa. Pintar bolinhas de acordo com o valor da tendência Mann Kendall.

    Figura com sazonalidade por estação no mapa. Pintar bolinhas de acordo com o valor da sazonalidade - indice de Markhan.


sec04_5.ipynb = Síntese das observações da qualidade do ar por região 

    Síntese por região - texto / tabela estática

    Interface com saúde  ANO QUE VEM – metodologia GARSC 


----------chpt05-----------
    Perspectivas de ampliação da rede e medidas de gestão das fontes de poluição  

----------chpt06-----------
    Comunicação e divulgação dos dados nos estados brasileiros 
        Tabela 15 – UFs brasileiras que possuem Relatórios de Avaliação de Qualidade do Ar. Ano Base dos relatórios.

----------chpt07----------- TALVEZ
    Publicações científicas em periódicos sobre a poluição no Brasil 

----------chpt08-----------
    Considerações finais 

---------------------
Referências 