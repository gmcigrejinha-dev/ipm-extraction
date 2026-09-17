import json
import time
from playwright.sync_api import sync_playwright


def extrair_na_nuvem():
    with sync_playwright() as p:
        print("🌐 Inicializando Chromium em Headless para GitHub Actions...")

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="pt-BR",
        )

        page = context.new_page()

        # Injeta falsificação de WebDriver
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # --- PARTE 1: Listener de Rede (Captura Passiva dos JSONs) ---
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

        # --- PARTE 2: Acesso ao Portal e Operações no Iframe ---
        print("🌐 Acessando o portal na nuvem...")
        page.goto(
            "https://igrejinha.atende.net/autoatendimento/servicos/consulta-de-licitacoes/detalhar/1",
            wait_until="networkidle",
        )

        print("⏳ Aguardando renderização completa do Iframe principal...")
        page.wait_for_selector("iframe", timeout=30000)
        time.sleep(3)

        # Conecta diretamente ao frame do formulário
        iframe = page.frame_locator("iframe").first

        print("🔍 Preenchendo a licitação 1044 no filtro...")
        
        # Localiza o campo de input
        campo_licitacao = iframe.get_by_label(
            "Primeiro valor para o filtro sobre o campo Número Licitação"
        )
        
        # Se o rótulo falhar no headless Linux, usa o fallback do seletor
        if campo_licitacao.count() == 0:
            campo_licitacao = iframe.locator("input[type='text'], input:not([type])").first

        campo_licitacao.wait_for(state="visible", timeout=15000)
        campo_licitacao.fill("1044")
        print("✔️ Licitação 1044 inserida no campo.")

        print("🖱️ Disparando o botão Consultar...")
        btn_consultar = iframe.locator("span.label_botao_acao:has-text('Consultar')").first
        
        # Garante visibilidade e força a execução do evento de clique JS da página
        btn_consultar.wait_for(state="visible", timeout=15000)
        btn_consultar.click(force=True)

        print("⏳ Aguardando retorno da busca AJAX...")
        page.wait_for_timeout(5000)

        # --- PARTE 3: Expansão de Chevrons e Seleção de Registro ---
        print("🔓 Expandindo agrupamentos fechados na tabela...")
        chevrons_fechados = iframe.locator(
            "span.fas.fa-chevron-down[name='no_fechado']"
        )
        qtd_fechados = chevrons_fechados.count()

        tentativas = 0
        while qtd_fechados > 0 and tentativas < 10:
            for i in range(qtd_fechados):
                try:
                    alvo = chevrons_fechados.nth(i)
                    alvo.scroll_into_view_if_needed()
                    alvo.click(force=True)
                    page.wait_for_timeout(300)
                except Exception:
                    pass

            chevrons_fechados = iframe.locator(
                "span.fas.fa-chevron-down[name='no_fechado']"
            )
            qtd_fechados = chevrons_fechados.count()
            tentativas += 1

        print("✔️ Agrupamentos processados!")

        print("☑️ Selecionando a linha referente à licitação 1044...")
        
        # Seletor resiliente: procura a linha tr ou diretamente o botão de seleção da tabela
        botao_selecao = iframe.locator("button[aria-label='deselecionado']").first
        botao_selecao.wait_for(state="visible", timeout=20000)
        botao_selecao.click(force=True)
        print("✔️ Linha selecionada!")

        page.wait_for_timeout(1000)

        print("📂 Clicando no botão Detalhar...")
        botao_detalhar = iframe.locator(
            "span.label_botao_acao:has-text('Detalhar')"
        ).first
        botao_detalhar.wait_for(state="visible", timeout=10000)
        botao_detalhar.click(force=True)

        page.wait_for_timeout(3000)

        # --- PARTE 4: Varredura das Abas e Disparo das Requisições ---
        abas = [
            "Geral",
            "Vencedores",
            "Contratos",
            "Ordens de Compra",
            "Empenhos",
            "Liquidações/Entregas",
        ]

        print("📑 Navegando pelas abas...")
        for aba in abas:
            try:
                print(f"👉 Acessando aba: {aba}")
                guia_aba = iframe.locator(f"text='{aba}'").first
                if guia_aba.is_visible():
                    guia_aba.click(force=True)
                    page.wait_for_timeout(2500)
            except Exception as e:
                print(f"⚠️ Não foi possível abrir a aba '{aba}': {e}")

        # --- SALVAMENTO DOS DADOS PARSADOS ---
        print("💾 Gravando dados no arquivo JSON...")
        with open("licitacao_1044_completa.json", "w", encoding="utf-8") as f:
            json.dump(dados_licitacao, f, indent=4, ensure_ascii=False)

        print(
            "🎉 Extração concluída com sucesso! 'licitacao_1044_completa.json' atualizado."
        )

        browser.close()


if __name__ == "__main__":
    extrair_na_nuvem()
