# radio

Sua rádio pessoal no **GitHub Pages**. Cada música é um arquivo MP3 em `tracks/` — a playlist, as páginas e o sitemap são gerados sozinhos no push.

> Sem banco de dados, sem código por música, sem stream. Só a pasta `tracks/`.

---

## Como funciona

Você faz uma coisa só: **joga um MP3 em `tracks/` e dá push**. O GitHub Actions faz o resto:

1. Escaneia `tracks/` e lê **artista** e **título** do nome do arquivo (`Artista - Título.mp3`).
2. Gera `tracks/playlist.json` + o manifesto embutido no player.
3. Gera **uma página por música** (`playlist/<slug>.html`), para cada faixa ter link próprio para compartilhar.
4. Gera `sitemap.xml`, remove páginas órfãs, **faz commit** e publica no Pages.

O player é o mesmo estilo LCD retrô do `radio.omarchy.org`, com tema de cores trocável no rodapé, controle de volume, e agora **repeat** (all / one) e **shuffle**.

![radio](https://raw.githubusercontent.com/iaeluk/radio/main/assets/images/screenshot-wide.png)

## Adicionar uma música

```bash
# coloque o arquivo na pasta
tracks/Pericles - Stand By Me (Ao Vivo Em São Paulo).mp3

# e suba
git add tracks/
git commit -m "add: Stand By Me (Ao Vivo Em São Paulo)"
git push
```

Pronto. Em alguns segundos a música aparece na playlist, ganha sua própria página e o site atualiza sozinho.

### Como nomear os arquivos

O nome do MP3 é a fonte de verdade:

```
Artista - Título.mp3        →  ✔ artista e título separados no " - "
Artista - Título (Ao Vivo).mp3  →  título completo, com sufixo
```

- O separador é `-` (hífen entre espaços).
- Acentos e emojis funcionam — o Pages serve **UTF-8** graças ao `.nojekyll`.
- Remova o MP3 e dê push → a faixa some da playlist e sua página é apagada.

## Rodar localmente

```bash
python3 tools/build.py          # gera playlist, páginas e sitemap
python3 -m http.server 8000     # abre http://localhost:8000
```

Ou, sem build (a rádio já nasce funcionando):

```bash
python3 -m http.server 8000
```

O player lê `tracks/playlist.json` direto, e ele já está commitado.

## Publicar no GitHub Pages

O repositório já tem o workflow `.github/workflows/build.yml`. Para **publicar**:

1. Crie o repositório (este já é o `radio`) e faça o push.
2. No GitHub, vá em **Settings → Pages → Build and deployment → Source** e escolha **GitHub Actions**.
3. Pronto — o primeiro push já publica em `https://iaeluk.github.io/radio/`.

> Publico via **GitHub Actions** (não "Deploy from a branch") para o deploy acontecer *sempre depois* do build, automático.

## Personalizar

Tudo opcional:

- **Nome/tagline da estação**: edite `STATION`, `STATION_NAME` e `SITE_DESC` no topo de `tools/build.py`.
- **Tema de cor**: o seletor no rodapé do player já troca os 24 temas (a escolha fica salva no navegador).
- **URL do site**: o `BASE` em `tools/build.py` controla canonical, sitemap e metadados.

## Estrutura

```
radio/
├── tracks/                     ← jogue os MP3 aqui
├── tools/
│   ├── build.py                build: playlist + páginas + sitemap (+ --check)
│   └── template.html           modelo de página do player
├── assets/
│   ├── css/                    visual LCD (estilo radio.omarchy.org)
│   ├── js/app.js               player (repeat, shuffle, temas, vol, seek)
│   ├── fonts/                  fontes do LCD
│   └── images/                 ícones e capturas
├── index.html                  página inicial (gerada)
├── playlist/                   uma página por música (gerada)
├── sitemap.xml                 (gerado)
├── .nojekyll                   Pages serve MP3/UTF-8 sem passar por Jekyll
└── .github/workflows/build.yml build automático + deploy no Pages
```

## Créditos

O visual do player é baseado no [radio.omarchy.org](https://radio.omarchy.org) (LCD retrô, temas de cor). O código é seu — adapte, compartilhe e divirta-se.