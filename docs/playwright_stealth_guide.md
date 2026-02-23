# Guia de Boas Práticas: Playwright Stealth (Evitando Detecção)

Quando automatizamos interações em redes sociais e plataformas complexas (como LinkedIn, Instagram, etc.) usando o Playwright, o comportamento padrão da ferramenta deixa "rastros" (fingerprints) que os sistemas anti-bot detectam facilmente.

Abaixo estão as melhores práticas para contornar essas detecções, divididas em **Configuração**, **Comportamento** e **Gestão de Sessão**.

---

## 1. Configuração e Fingerprint

Bots são frequentemente detectados logo na inicialização por causa das configurações padrão do navegador headless.

*   **Use o `playwright-stealth`:** Esta é a regra de ouro. O Playwright injeta variáveis globais no JavaScript (como `navigator.webdriver = true`). O pacote `playwright-stealth` mascara essas e outras propriedades conhecidas.
    ```python
    from playwright_stealth import stealth_sync
    # ...
    page = context.new_page()
    stealth_sync(page) # Aplique SEMPRE antes de navegar
    ```
*   **User-Agent Atualizado:** Nunca use o User-Agent padrão do Playwright (que costuma ser "HeadlessChrome"). Defina um User-Agent de um navegador moderno e comum.
    ```python
    ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    context = browser.new_context(user_agent=ua)
    ```
*   **Desabilite Flags de Automação:** Ao lançar o Chromium, passe argumentos para esconder a flag de controle automatizado.
    ```python
    browser = playwright.chromium.launch(args=['--disable-blink-features=AutomationControlled'])
    ```
*   **Viewport Realista:** Defina um tamanho de tela (viewport) realista. Tamanhos padrão de bots de teste (como 800x600) são suspeitos. Use resoluções comuns como `1280x800` ou `1920x1080`.

---

## 2. Comportamento Humanizado (Pacing & Interação)

A maior falha dos scrapers não é parecer um bot, mas ser **perfeito e rápido demais**. Humanos são caóticos.

*   **Evite o `page.evaluate("window.scrollTo(0, document.body.scrollHeight)")`:** Pular instantaneamente para o final da página num loop (o padrão em _infinite scrolls_) é um forte indicativo de bot.
    *   **A Prática Correta:** Use a simulação de scroll do mouse (`page.mouse.wheel`) com incrementos variados e tempos de pausa para "leitura".
    ```python
    # Scroll de uma quantidade aleatória (como se o usuário estivesse lendo)
    page.mouse.wheel(0, random.randint(400, 900))
    time.sleep(random.uniform(1, 3)) # Pausa para "ler"
    ```
*   **Bound Loops (Limites Rígidos):** SPAs (Single Page Applications) frequentemente geram loops infinitos. Nunca role a página indefinidamente. Coloque um teto rígido (`max_scrolls = 15`) para evitar que a plataforma veja um bot "trabalhando" infinitamente sem cansar.
*   **Jitter (Ruído) nos Delays:** Suas pausas não podem ser estáticas. Substitua `time.sleep(2)` por `time.sleep(random.uniform(1.5, 4.0))`.
*   **Wait on Deterministic UI Signals (Esperas Inteligentes):** Evite métodos como `page.wait_for_timeout(10000)` como estratégia principal de espera. Dez segundos pode ser muito rápido num dia de conexão ruim, ou muito lento e levantar suspeitas pela exatidão.
    *   **A Prática Correta:** Espere que elementos específicos da UI apareçam (ex: o número de posts na tela mudar).

---

## 3. Gestão de Sessão (State e Cookies)

Um bot sem estado sempre parece um usuário novo (e desconfiado) acessando a página.

*   **Persista e Reutilize o `storage_state`:** Sempre salve e carregue os cookies e o LocalStorage para evitar re-autenticações. Isso faz o bot parecer um usuário retornando.
    ```python
    context = browser.new_context(storage_state="state_linkedin.json")
    ```
*   **Não Reaproveite Contextos entre Sites Diferentes:** O perfil que o bot usa no LinkedIn não deve ter os cookies/histórico lidos acidentalmente por rotinas do Instagram. Mantenha os `storage_states` separados por domínio.
*   **Recupere-se do Block Limpando o State:** Se o acesso começar a dar 429 (Too Many Requests) ou a plataforma deslogar o bot, delete o `storage_state` atual e force um login manual ou uma nova sessão limpa. Repetir requisições com um cookie já "queimado" pela plataforma só piora o score do IP.
