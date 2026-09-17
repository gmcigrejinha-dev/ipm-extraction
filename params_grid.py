import json
import os
import time
from playwright.sync_api import sync_playwright


def extrair_licitacoes():
    is_ci = os.getenv("CI") == "true"
    licitacoes = ["1044", "42", "72"]

    with sync_playwright() as p:
        if is_ci:
            print("☁️ Rodando no GitHub Actions (Headless)...")
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080}, locale="pt-BR"
            )
        else:
            print("💻 Rodando local via CDP...")
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]

        for num_licitacao in licitacoes:
            print(f"\n========================================================")
            print(f"🚀 Processando Licitação: {num_licitacao}")
            print(f"========================================================")

            page = context.new_page() if not is_ci else context.new_page()
            dados_licitacao = {}

            def capturar_resposta(response):
                if "atende.php" in response.url and response.status == 200:
                    try:
                        if "json" in response.headers.get("content-type", ""):
                            json_payload = response.json()
                            if "rot=61072" in response.url:
                                dados_licitacao["Geral"] = json_payload
                            elif "rot=10027" in response.url:
                                dados_licitacao["Vencedores"] = json_payload
                            elif "rot=10062" in response.url:
                                dados_licitacao["Contratos"] = json_payload
                            elif "rot=10192" in response.url:
                                dados_licitacao["Ordens_de_Compra"] = (
                                    json_payload
                                )
                            elif "rot=10260" in response.url:
                                dados_licitacao["Empenhos"] = json_payload
                            elif "rot=10688" in response.url:
                                dados_licitacao["Liquidacoes"] = json_payload
                    except Exception:
                        pass

            page.on("response", capturar_resposta)

            try:
                page.goto(
                    "https://igrejinha.atende.net/autoatendimento/servicos/consulta-de-licitacoes/detalhar/1"
                )
                iframe = page.frame_locator("iframe").first

                campo_licitacao = iframe.get_by_label(
                    "Primeiro valor para o filtro sobre o campo Número Licitação"
                )
                campo_licitacao.wait_for(state="visible", timeout=15000)
                campo_licitacao.fill(num_licitacao)
                campo_licitacao.dispatch_event("change")
                campo_licitacao.dispatch_event("blur")

                iframe.locator(
                    "span.label_botao_acao:has-text('Consultar')"
                ).first.click(force=True)
                page.wait_for_timeout(4000)

                # Expansão de chevrons
                chevrons_fechados = iframe.locator(
                    "span.fas.fa-chevron-down[name='no_fechado']"
                )
                while chevrons_fechados.count() > 0:
                    for i in range(chevrons_fechados.count()):
                        try:
                            chevrons_fechados.nth(i).click(force=True)
                            page.wait_for_timeout(200)
                        except Exception:
                            pass
                    chevrons_fechados = iframe.locator(
                        "span.fas.fa-chevron-down[name='no_fechado']"
                    )

                # Seleção da linha
                celula = iframe.locator(
                    f"td[aria-description*='{num_licitacao}']"
                )
                linha = iframe.locator("tr", has=celula)
                botao_sel = linha.locator(
                    "button[aria-label='deselecionado']"
                ).first
                botao_sel.wait_for(state="visible", timeout=15000)
                botao_sel.click(force=True)

                page.wait_for_timeout(1000)
                iframe.locator(
                    "span.label_botao_acao:has-text('Detalhar')"
                ).first.click(force=True)
                page.wait_for_timeout(3000)

                # Abas
                for aba in [
                    "Geral",
                    "Vencedores",
                    "Contratos",
                    "Ordens de Compra",
                    "Empenhos",
                    "Liquidações/Entregas",
                ]:
                    try:
                        guia = iframe.locator(f"text='{aba}'").first
                        if guia.is_visible():
                            guia.click(force=True)
                            page.wait_for_timeout(2000)
                    except Exception:
                        pass

                nome_arquivo = f"licitacao_{num_licitacao}_completa.json"
                with open(nome_arquivo, "w", encoding="utf-8") as f:
                    json.dump(dados_licitacao, f, indent=4, ensure_ascii=False)
                print(f"💾 Salvo: {nome_arquivo}")

            except Exception as e:
                print(f"❌ Erro na licitação {num_licitacao}: {e}")
            finally:
                page.remove_listener("response", capturar_resposta)
                page.close()

        if not is_ci:
            browser.disconnect()
        else:
            browser.close()


if __name__ == "__main__":
    extrair_licitacoes()
