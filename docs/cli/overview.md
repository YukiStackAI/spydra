# Command Line Interface

Since v0.3, Spydra includes a powerful command-line interface that provides three main capabilities:

1. **Interactive Shell**: An interactive Web Scraping shell based on IPython that provides many shortcuts and useful tools
2. **Extract Commands**: Scrape websites from the terminal without any programming
3. **Utility Commands**: Installation and management tools

```bash
# Launch interactive shell
spydra shell

# Convert the content of a page to markdown and save it to a file
spydra extract get "https://example.com" content.md

# Get help for any command
spydra --help
spydra extract --help
```

## Requirements
This section requires you to install the extra `shell` dependency group, like the following:
```bash
pip install "spydra[shell]"
```
and the installation of the fetchers' dependencies with the following command
```bash
spydra install
```
This downloads all browsers, along with their system dependencies and fingerprint manipulation dependencies.