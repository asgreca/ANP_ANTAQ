# Extração e Monitoramento de Normas ANP e ANTAQ

Pipeline de dados automatizado para coleta, estruturação e monitoramento contínuo do arcabouço normativo da **Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP)** e da **Agência Nacional de Transportes Aquaviários (ANTAQ)**, desenvolvido para alimentar bases de conhecimento e sistemas de análise regulatória baseados em Inteligência Artificial.

---

## 1. O Problema e a Solução Técnica

### O Desafio Inicial
A necessidade de acessar o estoque e as atualizações de resoluções e normas da ANP e ANTAQ frequentemente se depara com a ideia de solicitar à TI das duas agências o desenvolvimento de uma API sob demanda, o que enfrenta dois grandes entraves:
1. Os sistemas de consulta usados pelas agências (`leis.org` para ANP e `sophia.antaq.gov.br` para ANTAQ) são softwares privados terceirizados. As equipes de TI das autarquias não possuem a posse do código para construir APIs personalizadas.
2. Ambos os portais possuem barreiras de segurança de rede (desafio de JavaScript / Cloudflare) que dificultam raspagens convencionais em servidores de dados.

### A Solução Implementada
Em vez de depender de desenvolvimentos externos ou de raspagens instáveis em sites terceirizados, o projeto atua **diretamente nas fontes oficiais primárias de validade jurídica**:
- **Diário Oficial da União (DOU Seção 1)**: Nenhuma resolução, portaria ou despacho regulatório tem validade legal no Brasil sem ser publicado na íntegra no DOU. O pipeline monitora a Seção 1 diariamente e extrai as matérias específicas da ANP e ANTAQ.
- **Portal da Legislação do Planalto**: Coleta as 7 leis federais estruturantes (Lei do Petróleo, Lei dos Portos, Lei do Gás, etc.) com texto consolidado oficial.
- **Compatibilidade Corporativa**: O sistema conta com extratores que não exigem navegadores headless (Chromium / Playwright), rodando perfeitamente em servidores restritos de empresas públicas e privadas.

---

## 2. Arquitetura do Projeto

O repositório foi desenhado para ser intuitivo, didático e modular:

```text
ANP_ANTAQ/
├── main.py                     # Ponto de entrada único: aciona todo o pipeline em 1 comando
├── README.md                   # Documentação passo a passo do projeto
├── requirements.txt            # Dependências essenciais e leves (zero Playwright obrigatório)
├── requirements-dev.txt        # Dependências opcionais para raspagem web via navegador
├── .env.example                # Modelo para credenciais do serviço INLABS
├── .gitignore                  # Arquivos ignorados pelo Git (dados, logs, caches)
├── src/
│   ├── __init__.py             # Inicializador do pacote Python
│   ├── config.py               # Configurações centrais, termos de busca e catálogo de leis
│   ├── leis_base.py            # Coletor das 7 Leis-Base Federais no Planalto (requests + bs4)
│   ├── dou_inlabs.py           # Coletor oficial do DOU via XML da Imprensa Nacional (Sem Playwright)
│   ├── dou_scraper.py          # Coletor alternativo do DOU via web (Playwright opcional)
│   └── resolucoes_consolidated_extractor.py # Extrator stealth para portais de acervo
└── scripts/
    ├── cron_daily.sh           # Script em shell para automação agendada no crontab
    └── deploy_vps.sh           # Script de sincronização e deploy no servidor VPS
```

---

## 3. Como Executar (Com Apenas Um Comando)

O projeto possui um orquestrador central (`main.py`) que executa todas as etapas necessárias de forma sequencial e controlada.

### Passo 1: Clonar o Repositório
```bash
git clone https://github.com/asgreca/ANP_ANTAQ.git
cd ANP_ANTAQ
```

### Passo 2: Criar o Ambiente Virtual e Instalar Dependências
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Passo 3: Executar o Pipeline Completo
Basta rodar o comando abaixo:
```bash
python main.py
```

O comando irá:
1. Verificar e baixar as 7 leis federais do setor no Planalto (armazenadas em `data/leis_base/`).
2. Conectar-se ao Diário Oficial da União da data de hoje, filtrar atos da ANP e ANTAQ e estruturá-los.
3. Exibir um resumo executivo com a contagem de normas salvas e o tempo de execução.

---

## 4. Modos de Execução do `main.py`

Você pode personalizar o comportamento do pipeline usando parâmetros de linha de comando:

### Coleta de uma data específica do DOU:
```bash
python main.py --data 25-09-2026
```

### Atualização forçada das leis-base federais:
```bash
python main.py --atualizar-leis
```

### Apenas atualização das leis federais (sem consultar o DOU):
```bash
python main.py --modo leis
```

### Forçar modo INLABS (XML oficial da Imprensa Nacional, sem navegador):
```bash
python main.py --modo inlabs
```

---

## 5. Como Funciona a Extração sem Playwright (Servidores Corporativos)

Muitos servidores corporativos barram navegadores automatizados como Chromium ou Playwright por restrições de segurança ou falta de bibliotecas visuais (X11).

Para contornar isso de forma nativa e sem quebras:
1. Criamos o módulo `src/dou_inlabs.py`, que utiliza o serviço oficial de dados abertos **INLABS** da Imprensa Nacional ([inlabs.in.gov.br](https://inlabs.in.gov.br)).
2. A Imprensa Nacional disponibiliza diariamente um pacote `.zip` com todas as matérias da Seção 1 em **XML estruturado**.
3. O script baixa o arquivo, descompacta em memória, filtra com XPath/XML os atos com tags de ANP e ANTAQ e salva os JSONs.
4. **Zero Chromium, zero Playwright, zero emulação de tela**. Apenas Python padrão e a biblioteca `requests`.

Para habilitar este modo, basta criar uma conta gratuita no [INLABS](https://inlabs.in.gov.br) e preencher no arquivo `.env`:
```bash
cp .env.example .env
# Edite com seu login e senha:
INLABS_EMAIL=seu_email@empresa.com.br
INLABS_PASSWORD=sua_senha
```

---

## 6. Automação Diária no Servidor (Crontab)

Para manter a base de dados do assistente regulatório sempre atualizada sem intervenção humana:

1. Abra a tabela de tarefas do servidor:
   ```bash
   crontab -e
   ```
2. Adicione a linha para execução automática todo dia útil às 06:30 da manhã:
   ```bash
   30 6 * * 1-5 /caminho/do/projeto/scripts/cron_daily.sh
   ```

O script gerará logs detalhados em `logs/dou_cron.log`.

---

## 7. Estrutura dos Dados Gerados

Todos os dados são salvos na pasta `data/`, divididos em dois formatos complementares:

### Formato JSON (Ideal para alimentação de bancos de dados vetoriais e RAG)
Cada ato contém campos estruturados:
```json
{
  "agencia": "ANP",
  "tipo_ato": "AUTORIZAÇÃO",
  "numero": "546",
  "ano": "2026",
  "titulo": "AUTORIZAÇÃO SPC-ANP Nº 546, DE 25 DE SETEMBRO DE 2026",
  "ementa": "Autoriza o exercício da atividade de comercialização de gás natural...",
  "orgao": "SUPERINTENDÊNCIA DE PRODUÇÃO DE COMBUSTÍVEIS",
  "autor": "Nome da Autoridade",
  "cargo": "Superintendente",
  "data_publicacao": "28-09-2026",
  "url": "https://www.in.gov.br/web/dou/-/...",
  "texto_integral": "O SUPERINTENDENTE DE PRODUÇÃO DE COMBUSTÍVEIS DA AGÊNCIA...",
  "coletado_em": "2026-09-28T12:16:45.123456"
}
```

### Formato Markdown (Ideal para leitura humana e inspeção rápida)
Salvo ao lado de cada ato com cabeçalho formatado e texto integral limpo.

---

## 8. Catálogo das Leis-Base Federais

| Identificador | Lei | Agência | Tema Central | Fonte Oficial |
|---|---|---|---|---|
| `lei_9478_1997` | Lei nº 9.478/1997 | ANP | Lei do Petróleo, cria a ANP e o CNPE | [Planalto](https://www.planalto.gov.br/ccivil_03/leis/l9478.htm) |
| `lei_12351_2010` | Lei nº 12.351/2010 | ANP | Regime de Partilha de Produção no Pré-Sal | [Planalto](https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/lei/l12351.htm) |
| `lei_14134_2021` | Lei nº 14.134/2021 | ANP | Nova Lei do Gás Natural | [Planalto](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14134.htm) |
| `lei_9847_1999` | Lei nº 9.847/1999 | ANP | Fiscalização do abastecimento nacional de combustíveis | [Planalto](https://www.planalto.gov.br/ccivil_03/leis/l9847.htm) |
| `lei_10233_2001` | Lei nº 10.233/2001 | ANTAQ | Criação da ANTAQ e reorganização do setor aquaviário | [Planalto](https://www.planalto.gov.br/ccivil_03/leis/leis_2001/l10233.htm) |
| `lei_12815_2013` | Lei nº 12.815/2013 | ANTAQ | Lei dos Portos e exploração de instalações portuárias | [Planalto](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12815.htm) |
| `lei_13848_2019` | Lei nº 13.848/2019 | GERAL | Lei Geral das Agências Reguladoras Federais | [Planalto](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2019/lei/l13848.htm) |
