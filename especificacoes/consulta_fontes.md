dentro da interface fontes web, preciso que crie duas abas:
1) consulta via prompt
esta aba deverá ter os seguintes campos:
- data de início (calendário) (obrigatório)
- data de término (calendário) (se nao for preenchido significa que deve considerar a data de hoje- atual)
- persona (texto) (obrigatório) (valor placeholder = um analista sênior de inteligênia de mercado, especializado em Inteligência Artificial e Inteligência Artificial Generativa)
- publico-alvo (obrigatório) (valor placeholder = consultor de IA que precisa se manter na vanguarda do setor para aconselhar seus clientes)
- formato de saída: campo selectbox (obrigatório) com as seguintes opcoes: .txt, .md, .pdf, .json, .xml
- segmentos (obrigatório) (valor placeholder = {saúde, educação,indústria})
- instruçoes gerais do prompt (texto opcional)

2) consulta via fontes
[sera especificado posteriormente. crie apenas a aba]

instrucoes gerais:
use sempre componentes streamlit.
sempre que possível, tente utilizar o padrão utilizado em outras interfaces, para o reaproveitamento de código.


=====
preciso das seguintes alteracoes na interface execucao fontes web aba consulta via prompt:

1) preciso que seja retirado o check (definir data de término?) e seja incluido um novo campo de formulário (obrigatório) para preenchimento da data de término da consulta. o formato da data deve ser dd/mm/aaaa. ambos os campos sao obrigatórios.

2) além disso, quero alteracoes nos campos persona, publico-alvo, segmentos e instrucoes gerais do prompt.
preciso que ao inves de trazer os valores como placeholder, preciso que traga já preenchidos com os valores que foram adicionados como placeholder como valores preenchidos por padrao nos respectivos campos.

3) preciso também, que crie na área de configuracoes, uma secao para cadastrar estes valores padroes que devem ser persistidos em banco de dados. ou seja, na interface de configuracoes, deverá ter uma area especifica chamada configuracoes da consulta info web (campos via prompt). nesta área, o usuário poderá altrerar os valores padroes para os campos persona, segmentos, publico-alvo e instrucoes gerais do prompt. 
Assim, sempre que o usuário abrir a interface execucao fontes web aba consulta via prompt, deverao ser trazidos os respectivos campos preenchidos com os valores cadastrados na area de configuracoes. o usuário pode alterar o valor no momento de executar a consulta via prompt. mas se entrar novamente na interface, os valores padroes devem ser retornados (conforme estao cadastrados na area de configuracoes). Se o usuário alterar o valor na area de configuracoes, na proxima vez que abrir a interface de consulta via prompt, os novos valors devem aparecer na interface.

4) preciso criar um novo campo chamado prompt dentro da aba consulta via prompt. será um campo de texto que receberá várias linhas de texto (campo obrigatório). o nome deste campo deverá ser "prompt da consulta".

5) assim como nos outros campos, o campo "prompt da consulta" também deverá estar disponível para cadastro nas configuracoes, na area especifica (onde estao os demais campos). também deverá ser persistido em banco de dados. ao abrir a aba consulta via web, o valor cadastrado para o campo "prompt da consulta" deverá ser exibido, mas o usuário poderá alterá-lo para a execucao. mas o valor a ser aberto na interface só poderá ser alterado em definitivo através das configuracoes na respectiva secao.

6) o prompt terá uma estrutura parecida com essa:

"""
    <INSTRUCOES_GERAIS>
        [valor das instrucoes gerais]
    </INSTRUCOES_GERAIS>


    <PROMPT>
    Atue como {valor do campo persona}.
    Seu objetivo é compilar um briefing semanal conciso, abrangente e estratégico para a semana de {valor do campo data de inicio} a {valor do campo data de termino}. 
    O público-alvo é {valor do campo publico-alvo}. 
    O formato final deve ser em {valor do campo formato saida}, 
    A saída deve conforme a estrutura abaixo:
    - Para cada item, forneça um resumo curto (1-2 frases) e, sempre que possível, o link para a fonte original. 
    - Priorize fontes de alta credibilidade (ex: The Verge, TechCrunch, blogs oficiais das empresas, artigos de pesquisa, relatórios de consultorias). 

    # Briefing Semanal de IA e IA Generativa 

    **Período:** {valor do campo data de inicio} a {valor do campo data de fim} 

    ## 1. Resumo Executivo
    * **Destaque 1:** [Resumo do fato mais importante da semana] [Link]
    * **Destaque 2:** [Resumo do segundo fato mais importante] [Link]
    * **Destaque 3:** [Resumo do terceiro fato mais importante] [Link]
    * **Destaque 4:** [Resumo do quarto fato mais importante] [Link]
    * **Destaque 5:** [Resumo do quinto fato mais importante] [Link]


    ## 2. Notícias e Anúncios de Destaque
    * **Big Techs:** 
    * [Nome da Empresa]: [Resumo da notícia] - [Link] 

    * **Startups e Investimentos:** 
    * [Nome da Startup]: [Resumo da notícia sobre investimento ou aquisição] - [Link] 

    * **Regulamentação e Ética:** 
    * [Tópico ou Região]: [Resumo da notícia] - [Link] 



    ## 3. Inovações em Modelos 
    * **Novos Lançamentos:** 
    * [Nome do Modelo] por [Empresa/Organização]: [Descrição das capacidades] - [Link] 
    * **Atualizações Relevantes:** 
    * [Nome do Modelo Existente]: [Descrição da atualização] - [Link] 
    * **Destaques Open Source:** 
    * [Nome do Modelo Open Source]: [Descrição e motivo do destaque] - [Link] 


    ## 4. Novas Ferramentas e Aplicações 
    * **Para Desenvolvedores:** 
    * [Nome da Ferramenta/Biblioteca]: [Descrição da sua função] - [Link] 
    * **Para Usuários Finais:** 
    * [Nome do Aplicativo]: [Descrição da sua função] - [Link] 
    * **Caso de Uso de Impacto:** 
    * [Empresa/Setor]: [Descrição de como a IA foi aplicada e o resultado] - [Link] 


    ## 5. Análises de Mercado e Insights Estratégicos 
    * **Insights de Consultorias:** 
    * [Nome da Consultoria (ex: Gartner)]:[Principal insight do relatório/artigo] - [Link] 
    * **Tendência Emergente:** 
    * [Nome da Tendência]: [Breve explicação sobre o que é e por que é importante] - [Link] 
    * **Análise de Influenciador:** 
    * [Nome do Influenciador]: [Resumo da sua análise ou opinião] - [Link para post/vídeo]

    # Análise IA por Segmento

    Faca a análise, conforme estrutura abaixo, para cada um dos segmentos em {valor do campo segmentos}. 
    ## Segmento {valor do campo segmentos}

    ### 1. Análises de Mercado e Insights Estratégicos 
    * **Insights de Consultorias:** 
    * [Nome da Consultoria (ex: Gartner)]:[Principal insight do relatório/artigo] - [Link] 
    * **Tendência Emergente:** 
    * [Nome da Tendência]: [Breve explicação sobre o que é e por que é importante] - [Link] 
    * **Análise de Influenciador:** 
    * [Nome do Influenciador]: [Resumo da sua análise ou opinião] - [Link para post/vídeo]


    ### 2. Inovação em Ferramentas de IA Generativa (Grandes Empresas)
    * **Cases de inovação com implantação de IA Generativa:** 
    * [Nome da Empresa ]:[Breve descrição do processo de implantação da IA Generatica na empresa, benefícios/resultados] - [Link] 
    * **Notícias sobre automatização de tarefas/rotinas:** 
    * [Nome da Empresa]: [Breve descrição do processo/tarefa/rotina automatizada] - [Link] 


    ### 3. Inovação em Ferramentas de IA Generativa (Pequenas e Médias Empresas)
    * **Cases de inovação com implantação de IA Generativa:** 
    * [Nome da Empresa ]:[Breve descrição do processo de implantação da IA Generatica na empresa, benefícios/resultados] - [Link] 
    * **Notícias sobre automatização de tarefas/rotinas:** 
    * [Nome da Empresa]: [Breve descrição do processo/tarefa/rotina automatizada] - [Link] 

    </PROMPT>
"""

7) ainda na interface da aba Consulta via prompt, deverá haver um campo para selecao do modelo LLM a ser utilizado para execucao do prompt. (campo obrigatório). os valores desse campo deverao vir dos valores cadastrados em cadastro de LLM.

8) abaixo deverá ser criado um botao executar prompt. ao clicar neste botao, deverá ser realizadas todas consistencias da interface e consistencias necessárias para execucao do prompt. se tudo estiver ok, a interface deverá executar o prompt com os valores das variaveis preechidas.

9) durante a execucao do prompt, a interface deverá mostrar o andamento da execucao do prompt, com as etapas que estao sendo executadas e uma barra de progresso com st.progress.

10) quando finalizado, a interface deverá mostrar dados da execucao como :
data/hora inicio execucao:
data/hora termino execucao:
tempo total da exeucao:
modelo LLM utilizado:
total de tokens enviados:
total de tokens recebidos:
custo estimado da consulta:
prompt executado:
resultado do prompt (no formato solicitado):
link para download do arquivo gerado:

a interface deverá mostrar em tela, no arquivo de saída solicitado e no arquivo de log, conforme formato solicitado, o resultado da consulta do prompt.

=======

na interface da aba consulta via prompt, gostaria de adicionar as seguintes alteracoes:

1) abaixo do campo instrucoes gerais do prompt, preciso que adicione um botao chamado "atualizar prompt de consulta". ao clicar neste botao, a interface atualiza o texto do prompt de consulta do campo abaixo, com os respectivos valores preenchidos. o valor do campo prompt de consulta é o prompt final que será enviado para a LLM.


======

na interface da aba consulta via prompt, gostaria de adicionar as seguintes alteracoes:

1) o campo data de inicio deverá vir com o valor padrao D-1 (ou seja, a data de hoje - 1 dia, no formato dd/mm/aaaa, por exemplo se hoje é dia 22/01/2024, o valor padrao deverá ser 23/01/2024).

2) o campo data de termino deerá vir com a data do dia de hoje (no formato dd/mm/aaaa).

3) ao clicar em atualizar prompt de consulta, a interface deverá fazer as seguintes alteracoes no conteudo do prompt da consulta.
3.1) substituir {PERSONA} pelo conteúdo do campo "Persona" do formulario.
3.2) substituir {DATA_INICIAL} pelo conteúdo do campo "Data de início" do formulario.
3.3) substituir {DATA_FINAL} pelo conteúdo do campo "Data de término" do formulario.
3.4) substituir {PUBLICO_ALVO} pelo conteudo do campo "Público-alvo" do formulário.
3.5) substituir {SEGMENTOS} pelo conteudo do campo "Segmentos" do formulário.


====

na interface da aba consulta via prompt, gostaria de adicionar as seguintes alteracoes:
3.1) substituir {FORMATO_SAIDA} pelo conteúdo do campo "Formato de saída" do formulario.
3.2) retire o campo Instruções gerais do prompt

====