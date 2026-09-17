import json
import time
from playwright.sync_api import sync_playwright


def extrair_na_nuvem():
    with sync_playwright() as p:
        print("🌐 Inicializando Chromium (1920x1080) Headless na nuvem...")
        # 1. Força a resolução de tela Desktop (1920x1080) igual ao VS Code local
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--window-size=1920,1080",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="pt-BR",
        )
        page = context.new_page()

        # --- PARTE 1: Configuração do Listener de Rede ---
        dados_licitacao = {}

        def capturar_resposta(response):
            if "atende.php" in response.url and response.status == 200:
                try:
                    json_payload = response.json()
                    print(
                        f"📡 API Capturada com Sucesso! [URL: {response.url[:60]}...]"
                    )

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
                    pass

        page.on("response", capturar_resposta)

        # --- PARTE 2: Acesso à Página e Preenchimento ---
        print("🌐 Acessando o portal na nuvem...")
        page.goto(
            "https://igrejinha.atende.net/autoatendimento/servicos/consulta-de-licitacoes/detalhar/1",
            wait_until="networkidle",
        )

        print("⏳ Aguardando o iframe ser renderizado pelo servidor...")
        # Espera ativamente a tag iframe surgir na página
        page.wait_for_selector("iframe", state="attached", timeout=30000)
        time.sleep(3)  # Pausa de estabilização do carregamento JS interno

        iframe = page.frame_locator("iframe").first

        print("🔍 Buscando o campo da licitação 1044...")

        # Estratégia de busca com Fallbacks inteligentes
        try:
            # Tentativa 1: O mesmo rótulo do seu VS Code
            campo_licitacao = iframe.get_by_label(
                "Primeiro valor para o filtro sobre o campo Número Licitação"
            )
            campo_licitacao.wait_for(state="visible", timeout=10000)
            campo_licitacao.fill("1044")
        except Exception:
            print(
                "⚠️ Rótulo exato não encontrado imediatamente, tentando seletor genérico do input..."
            )
            # Tentativa 2: Busca pelo primeiro campo de texto ativo do formulário
            inputs_texto = iframe.locator(
                "input[type='text'], input:not([type])"
            )
            inputs_texto.first.wait_for(state="visible", timeout=10000)
            inputs_texto.first.fill("1044")

        print("🖱️ Clicando em Consultar...")
        # Clica no botão Consultar dentro do iframe
        btn_consultar = iframe.locator(
            "span.label_botao_acao:has-text('Consultar')"
        ).first
        btn_consultar.wait_for(state="visible", timeout=10000)
        btn_consultar.click()

        print("⏳ Aguardando a tabela de resultados carregar...")
        page.wait_for_timeout(4000)

        # --- PARTE 3: Expansão de Chevrons e Seleção ---
        print("🔓 Expandindo agrupamentos fechados na tabela...")
        chevrons_fechados = iframe.locator(
            "span.fas.fa-chevron-down[name='no_fechado']"
        )
        qtd_fechados = chevrons_fechados.count()

        while qtd_fechados > 0:
            for i in range(qtd_fechados):
                try:
                    alvo = chevrons_fechados.nth(i)
                    alvo.scroll_into_view_if_needed()
                    alvo.click(force=True)
                    page.wait_for_timeout(400)
                except Exception:
                    pass

            chevrons_fechados = iframe.locator(
                "span.fas.fa-chevron-down[name='no_fechado']"
            )
            qtd_fechados = chevrons_fechados.count()

        print("✔️ Todos os agrupamentos foram expandidos!")

        print("☑️ Selecionando a licitação 1044 na tabela...")
        celula_licitacao = iframe.locator("td[aria-description*='1044']")
        linha_resultado = iframe.locator("tr", has=celula_licitacao)
        botao_selecao = linha_resultado.locator(
            "button[aria-label='deselecionado']"
        )

        botao_selecao.wait_for(state="visible", timeout=15000)
        botao_selecao.click()
        print("✔️ Linha selecionada com sucesso!")

        page.wait_for_timeout(1000)

        print("📂 Abrindo detalhes...")
        botao_span = iframe.locator(
            "span.label_botao_acao:has-text('Detalhar')"
        )
        botao_span.wait_for(state="visible", timeout=10000)
        botao_span.click()

        page.wait_for_timeout(3000)

        # --- PARTE 4: Varredura das Abas ---
        abas = [
            "Geral",
            "Vencedores",
            "Contratos",
            "Ordens de Compra",
            "Empenhos",
            "Liquidações/Entregas",
        ]

        print("📑 Iniciando varredura das abas...")
        for aba in abas:
            try:
                print(f"👉 Clicando na aba: {aba}")
                guia_aba = iframe.locator(f"text='{aba}'")
                if guia_aba.is_visible():
                    guia_aba.click()
                    page.wait_for_timeout(2500)
            except Exception as e:
                print(f"⚠️ Não foi possível abrir a aba '{aba}': {e}")

        # --- SALVAMENTO DOS DADOS ---
        print("💾 Salvando os dados extraídos...")
        with open("licitacao_1044_completa.json", "w", encoding="utf-8") as f:
            json.dump(dados_licitacao, f, indent=4, ensure_ascii=False)

        print(
            "🎉 Processo concluído! Arquivo 'licitacao_1044_completa.json' gerado com sucesso."
        )

        browser.close()


if __name__ == "__main__":
    extrair_na_nuvem()
