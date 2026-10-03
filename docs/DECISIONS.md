# DECISIONS log

Format: ID, date, question, options, choice, reason, how to reverse.

| ID | Date | Question | Choice | Reason | Reverse |
|---|---|---|---|---|---|
| D-001 | 2026-10-03 | Where to work? | Real project folder with its own git repo (not a worktree of an unrelated repo) | First session was blocked by a hook on the real folder | n/a |
| D-002 | 2026-10-03 | Python / OpenSeesPy version | Python 3.12.14 + openseespy 3.8.0.0 | `openseespy 3.7.0.3` on Windows is guarded for py3.11 but its pyd links python312.dll ("DLL load failed"); 3.8.0.0 works on 3.12 | Recreate `.venv` with 3.11 and pin 3.7.0.3 |
| D-003 | 2026-10-03 | `PROJECT.md` vs `project.md` | Renamed to `project.md` (as CLAUDE.md refers to it) | Naming consistency | `git mv` back |
| D-004 | 2026-10-03 | Remote | Owner's existing repo https://github.com/git-tejassh/rcOptimization as `origin`; `gh` not installed, plain `git push`. No tokens ever written | Owner said repo exists | `git remote set-url` |
| D-005 | 2026-10-03 | STAAD binary units | `.rea/.dsp` are kip / inch internally | Verified against DL reaction sum (3952.34 kip = 17,580 kN) | n/a |
