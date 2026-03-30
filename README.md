# ofs — Optimized for Speed

A collection of hacky, opinionated tricks for getting faster on a Mac. Hyper key combos, home row chords, pane navigation without thinking, leader sequences committed to muscle memory — the kind of stuff that makes you unreasonably fast once it's wired in.

The problem is that these bindings live across 7 different tools, each with its own config format, notation, and storage mechanism. You forget what's bound where. You accidentally shadow a binding. You want to find a free hyper key slot and have to check six places.

`ofs` fixes that. One command, one file, every keybinding you have.

## The stack

| Tool | What it does | Config format |
|---|---|---|
| **Karabiner-Elements** | Key remapping, hyper key, simultaneous keys, home row chords | JSON |
| **BetterTouchTool** | Hyper key → app launch, window management, custom triggers | SQLite |
| **tmux** | Pane/window/session navigation, copy mode | Text (bind directives) |
| **neovim** | Editor keymaps, leader sequences, plugin shortcuts | Lua |
| **Zed** | Editor keymaps | JSONC |
| **Homerow** | Keyboard-driven clicking, scrolling | plist |
| **Raycast** | Launcher shortcuts | Manual (GUI-only) |

## What ofs does

Extracts keybindings from all of the above, normalizes the notation (every tool writes modifiers differently), and dumps them into a single searchable file.

```
./ofs build                        # Extract all → bindings.tsv
./ofs build --format json|md|tsv   # Choose output format
./ofs build --only tmux,neovim     # Subset of sources
./ofs search <pattern>             # Regex search through last build
./ofs list-sources                 # Show configured sources + paths
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

All modifiers normalize to `ctrl`, `opt`, `shift`, `cmd`, `fn`. When all four of ctrl+opt+shift+cmd are present, they collapse to `hyper`.

## Setup

Python 3, stdlib only, zero dependencies. Clone and run.

```bash
git clone https://github.com/CaptainCrouton89/ofs.git
cd ofs
./ofs build
```

Default source paths are in `ofs.defaults.json`. To override locally, create `ofs.config.json` (gitignored):

```json
{
  "sources": {
    "tmux": { "path": "~/.tmux.conf" },
    "neovim": { "enabled": false }
  }
}
```
