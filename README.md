# ofs

Keybindings are scattered across Karabiner, tmux, neovim, Zed, BetterTouchTool, Homerow, and Raycast. `ofs` extracts them all into a single searchable file.

Python 3, stdlib only, zero dependencies.

## Usage

```
./ofs build                        # Extract all → bindings.tsv
./ofs build --format json|md|tsv   # Choose output format
./ofs build --only tmux,neovim     # Subset of sources
./ofs build -o custom.tsv          # Custom output path
./ofs list-sources                 # Show configured sources + paths
./ofs search <pattern>             # Regex search through last build
```

Example output:

```
tool        key              action                   context   source
karabiner   cmd+h            Right cmd+hjkl → arrows  global    karabiner.json
tmux        ctrl+h           Select pane left         root      tmux.conf
neovim      space+g+g        LazyGit                  normal    plugins/git.lua
btt         hyper+d          Send Keyboard Shortcut   global    btt_data_store...
homerow     hyper+f          Homerow Labels           global    com.superultra...
```

## Configuration

**`ofs.defaults.json`** ships with default paths for all sources. To override locally, create **`ofs.config.json`** (gitignored) — it shallow-merges per source key:

```json
{
  "sources": {
    "tmux": { "path": "~/.tmux.conf" },
    "neovim": { "enabled": false }
  }
}
```

## Adding a source

1. Create `extractors/foo.py` with `extract(config: dict) -> list[Keybinding]`
2. Add `"foo": "extractors.foo"` to the `EXTRACTORS` dict in `ofs`
3. Add default config to `ofs.defaults.json`

## How it works

Each extractor reads its tool's config format (JSON, plist, SQLite, regex on text) and returns a list of `Keybinding` objects. All key combos are normalized to a canonical form: modifiers sorted as `ctrl+opt+shift+cmd+fn`, with `ctrl+opt+shift+cmd` collapsed to `hyper`.

| Source | Raw notation | Normalized |
|---|---|---|
| Karabiner | `left_command` + `left_shift` + `g` | `shift+cmd+g` |
| tmux | `C-h` | `ctrl+h` |
| neovim | `<C-d>` | `ctrl+d` |
| Zed | `cmd-shift-g` | `shift+cmd+g` |
| BTT | keycode `2` + bitmask `1966080` | `hyper+d` |
| Homerow | `⌃⌥⇧⌘F` | `hyper+f` |
