import json
import time
from playwright.sync_api import sync_playwright


def extrair_na_nuvem():
    with sync_playwright() as p:
        # ⚠️ MUDANÇA CHAVE: Em vez de usar connect_over_cdp, abrimos o Chromium nativo do Playwright em headless
        print("🌐 Inicializando Chromium em Headless na nuvem...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # O restante da sua lógica de interceptação, cliques no iframe,
        # expansão de chevrons e navegação pelas abas permanece EXATAMENTE igual.

        # ... [MANTENHA TODO O SEU CÓDIGO DE CLIQUES E LISTENERS AQUI] ...

        capturas = []

        def monitorar_respostas(response):
            if "atende.php" in response.url and response.status == 200:
                try:
                    if "json" in response.headers.get("content-type", ""):
                        capturas.append({"url": response.url, "dados": response.json()})
                except Exception:
                    pass

        page.on("response", monitorar_respostas)
        # -------------------------------------------------------------

        # --- PARTE 2: Acesso à Página e Preenchimento Seguro ---
        # --- PARTE 2: Acesso à Página e Preenchimento com Seletor Exato ---
        print("🌐 Acessando o portal na sessão real...")
        page.goto("https://igrejinha.atende.net/autoatendimento/servicos/consulta-de-licitacoes/detalhar/1")

        print("🔍 Buscando a licitação 1044...")

        # Guarda a referência do iframe
        iframe = page.frame_locator("iframe").first

        # Preenche o campo dentro do iframe
        campo_licitacao = iframe.get_by_label("Primeiro valor para o filtro sobre o campo Número Licitação")
        campo_licitacao.fill("1044")

        # Clica no botão DENTRO do iframe (usando a variável iframe)
        iframe.locator("span.label_botao_acao:has-text('Consultar')").click()
        # -------------------------------------------------------------
        # -------------------------------------------------------------
        # -------------------------------------------------------------

        # --- PARTE 3: Seleção da Tabela e Abertura do Modal ---
        iframe.locator("span.label_botao_acao:has-text('Consultar')").click()

        print("⏳ Aguardando a tabela de resultados carregar...")
        page.wait_for_timeout(3000)

        print("🔓 Expandindo agrupamentos fechados na tabela...")

        # 1. Localiza os ícones de chevron que estão fechados
        chevrons_fechados = iframe.locator("span.fas.fa-chevron-down[name='no_fechado']")
        qtd_fechados = chevrons_fechados.count()

        while qtd_fechados > 0:
            for i in range(qtd_fechados):
                try:
                    alvo = chevrons_fechados.nth(i)
                    # Garante que o elemento está visível antes de tentar
                    alvo.scroll_into_view_if_needed()
                    
                    # Força o clique diretamente no elemento sem disparar rolagem brusca do navegador
                    alvo.click(force=True)
                    
                    page.wait_for_timeout(300) # Pausa rápida para a animação abrir
                except Exception:
                    pass
                    
            # Atualiza a contagem para verificar se novos agrupamentos internos apareceram
            chevrons_fechados = iframe.locator("span.fas.fa-chevron-down[name='no_fechado']")
            qtd_fechados = chevrons_fechados.count()

        print("✔️ Todos os agrupamentos foram expandidos!")

        print("☑️ Selecionando o resultado na tabela...")

        # Agora que a tabela está inteira aberta, a célula 1044 estará visível no DOM
        celula_licitacao = iframe.locator("td[aria-description*='1044']")
        linha_resultado = iframe.locator("tr", has=celula_licitacao)
        botao_selecao = linha_resultado.locator("button[aria-label='deselecionado']")

        botao_selecao.wait_for(state="visible", timeout=10000)
        botao_selecao.click()
        print("✔️ Linha selecionada com sucesso!")

        page.wait_for_timeout(1000)

        print("📂 Abrindo detalhes...")

        botao_span = iframe.locator("span.label_botao_acao:has-text('Detalhar')")
        botao_span.wait_for(state="visible", timeout=10000)
        botao_span.click()

        page.wait_for_timeout(2000)
        # -------------------------------------------------------------

        # --- PARTE 4: Varredura das Abas e Salvamento do JSON ---
        # Dicionário que guardará os JSONs extraídos de cada aba
        dados_licitacao = {}

        # Lista com os nomes das abas conforme aparecem na tela
        abas = ["Geral", "Vencedores", "Contratos", "Ordens de Compra", "Empenhos", "Liquidações/Entregas"]

        # --- CONFIGURAÇÃO DO LISTENER DE REDE ---
        def capturar_resposta(response):
            # Verifica se a resposta vem do endpoint de dados e teve sucesso (status 200)
            if "atende.php" in response.url and response.status == 200:
                try:
                    # Tenta converter o conteúdo da resposta para JSON
                    json_payload = response.json()
                    
                    # Armazena o JSON associando à URL ou rota
                    print(f"📡 API Capturada com Sucesso! [URL: {response.url[:60]}...]")
                    
                    # Mapeamento dinâmico baseado na rota
                    if "rot=61072" in response.url:
                        dados_licitacao["Geral"] = json_payload
                    elif "rot=10027" in response.url:
                        dados_licitacao["Vencedores"] = json_payload
                    elif "rot=10062" in response.url:
                        dados_licitacao["Contratos"] = json_payload
                    elif "rot=10192" in response.url:
                        dados_licitacao["Ordens_de_Compra"] = json_payload
                    elif "rot=10260" in response.url:
                        dados_licitacao["Empenhos"] = json_payload
                    elif "rot=10688" in response.url:
                        dados_licitacao["Liquidacoes"] = json_payload
                except Exception:
                    # Caso a resposta não seja um JSON válido, apenas ignora
                    pass

        # Ativa o ouvinte na página principal
        page.on("response", capturar_resposta)


        # --- VARREDURA DAS ABAS NO IFRAME ---
        print("📑 Iniciando varredura das abas para disparo das requisições...")

        for aba in abas:
            try:
                print(f"👉 Clicando na aba: {aba}")
                
                # Localiza o botão/guia da aba dentro do iframe e clica
                guia_aba = iframe.locator(f"text='{aba}'")
                if guia_aba.is_visible():
                    guia_aba.click()
                    # Pausa para a requisição de rede acontecer e ser ouvida pelo listener
                    page.wait_for_timeout(2000)
            except Exception as e:
                print(f"⚠️ Não foi possível abrir a aba '{aba}': {e}")

        # --- SALVAMENTO DOS DADOS PARSADOS EM JSON ---
        import json

        print("💾 Salvando os dados extraídos...")
        with open("licitacao_1044_completa.json", "w", encoding="utf-8") as f:
            json.dump(dados_licitacao, f, indent=4, ensure_ascii=False)

        print("🎉 Processo concluído! Arquivo 'licitacao_1044_completa.json' gerado.")
        # -------------------------------------------------------------
        # -------------------------------------------------------------
        browser.close()


if __name__ == "__main__":
    extrair_na_nuvem()
