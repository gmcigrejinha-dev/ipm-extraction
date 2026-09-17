import json
import time
from playwright.sync_api import sync_playwright


def extrair_na_nuvem():
    with sync_playwright() as p:
        print("🌐 Inicializando Chromium no modo Headless...")

        # 1. Parâmetros avançados para disfarçar a automação no modo Headless
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1920,1080",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="pt-BR",
        )

        page = context.new_page()

        # Injeta script para remover a flag de automação visível do navegador
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # --- PARTE 1: Listener de Rede ---
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

        # --- PARTE 2: Acesso e Captura Dinâmica do Frame de Conteúdo ---
        print("🌐 Acessando o portal na nuvem...")
        page.goto(
            "https://igrejinha.atende.net/autoatendimento/servicos/consulta-de-licitacoes/detalhar/1",
            wait_until="networkidle",
        )

        print("⏳ Localizando o frame ativo do formulário...")
        # Aguarda a criação de frames no DOM da página
        page.wait_for_timeout(5000)

        # Varre todos os frames da página até achar aquele que contém os elementos de filtro
        target_frame = None
        for frame in page.frames:
            try:
                # Procura se o frame possui o campo de filtro
                if frame.locator(
                    "span.label_botao_acao:has-text('Consultar')"
                ).count() > 0 or frame.locator("input").count() > 0:
                    target_frame = frame
                    print(f"✅ Frame ativo encontrado: {frame.url[:60]}...")
                    break
            except Exception:
                continue

        # Se a varredura por frames não encontrar, usa o frame_locator padrão como contingência
        if not target_frame:
            print("⚠️ Usando seletor padrão de iframe...")
            target_frame = page.frame_locator("iframe").first

        print("🔍 Preenchendo a licitação 1044...")

        # Preenche o filtro dentro do frame correto
        campo_preenchido = False

        # Tentativa 1: Rótulo direto
        try:
            campo = target_frame.get_by_label(
                "Primeiro valor para o filtro sobre o campo Número Licitação"
            )
            campo.wait_for(state="visible", timeout=5000)
            campo.fill("1044")
            campo_preenchido = True
        except Exception:
            pass

        # Tentativa 2: Busca por todos os inputs visíveis caso o rótulo mude
        if not campo_preenchido:
            try:
                inputs = target_frame.locator("input[type='text'], input:not([type])")
                for i in range(inputs.count()):
                    inp = inputs.nth(i)
                    if inp.is_visible():
                        inp.fill("1044")
                        campo_preenchido = True
                        break
            except Exception as e:
                print(f"❌ Falha ao preencher campo: {e}")

        print("🖱️ Clicando em Consultar...")
        # Tenta localizar o botão por texto/classe via seletores alternativos
        btn_consultar = target_frame.locator(
            "span.label_botao_acao:has-text('Consultar'), "
            "button:has-text('Consultar'), "
            "div.btn:has-text('Consultar'), "
            "[aria-label*='Consultar']"
        ).first
        
        btn_consultar.wait_for(state="visible", timeout=10000)
        btn_consultar.click(force=True)

        print("⏳ Aguardando a tabela de resultados carregar...")
        page.wait_for_timeout(4000)

        # --- PARTE 3: Expansão de Chevrons e Seleção ---
        print("🔓 Expandindo agrupamentos fechados na tabela...")
        chevrons_fechados = target_frame.locator(
            "span.fas.fa-chevron-down[name='no_fechado']"
        )
        qtd_fechados = chevrons_fechados.count()

        while qtd_fechados > 0:
            for i in range(qtd_fechados):
                try:
                    alvo = chevrons_fechados.nth(i)
                    alvo.scroll_into_view_if_needed()
                    alvo.click(force=True)
                    page.wait_for_timeout(300)
                except Exception:
                    pass

            chevrons_fechados = target_frame.locator(
                "span.fas.fa-chevron-down[name='no_fechado']"
            )
            qtd_fechados = chevrons_fechados.count()

        print("✔️ Todos os agrupamentos foram expandidos!")

        print("☑️ Selecionando a licitação 1044 na tabela...")
        celula_licitacao = target_frame.locator("td[aria-description*='1044']")
        linha_resultado = target_frame.locator("tr", has=celula_licitacao)
        botao_selecao = linha_resultado.locator(
            "button[aria-label='deselecionado']"
        )

        botao_selecao.wait_for(state="visible", timeout=15000)
        botao_selecao.click()
        print("✔️ Linha selecionada com sucesso!")

        page.wait_for_timeout(1000)

        print("📂 Abrindo detalhes...")
        botao_span = target_frame.locator(
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
                guia_aba = target_frame.locator(f"text='{aba}'")
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
