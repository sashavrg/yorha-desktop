vim.cmd("highlight clear")
if vim.fn.exists("syntax_on") == 1 then vim.cmd("syntax reset") end
vim.o.background = "dark"
vim.g.colors_name = "yorha"
local p = { bg="#242220", paper="#2f2c28", fg="#c8c2a9", muted="#9b9384", line="#565047", red="#c18469", green="#9aaa7b", blue="#8da3a0", purple="#ae96a7", gold="#b3a073" }
local function hi(name, fg, bg, extra)
    local spec = extra or {}
    spec.fg = fg; spec.bg = bg
    vim.api.nvim_set_hl(0, name, spec)
end
hi("Normal", p.fg, p.bg)
hi("NormalFloat", p.fg, p.paper)
hi("FloatBorder", p.fg, p.paper)
hi("Comment", p.muted, nil, {italic=true})
hi("Constant", p.gold); hi("String", p.green); hi("Number", p.gold)
hi("Identifier", p.fg); hi("Function", p.blue)
hi("Statement", p.fg, nil, {bold=true}); hi("PreProc", p.purple)
hi("Type", p.blue); hi("Special", p.purple); hi("Delimiter", p.muted)
hi("LineNr", p.muted, p.bg); hi("CursorLineNr", p.fg, p.paper, {bold=true})
hi("CursorLine", nil, p.paper); hi("SignColumn", p.muted, p.bg)
hi("Visual", p.paper, p.fg); hi("Search", p.fg, p.line); hi("IncSearch", p.paper, p.fg)
hi("Pmenu", p.fg, p.paper); hi("PmenuSel", p.paper, p.fg)
hi("StatusLine", p.paper, p.fg); hi("StatusLineNC", p.muted, p.paper)
hi("WinSeparator", p.line, p.bg)
hi("DiagnosticError", p.red); hi("DiagnosticWarn", p.gold)
hi("DiagnosticInfo", p.blue); hi("DiagnosticHint", p.green)
hi("DiffAdd", p.green, p.paper); hi("DiffDelete", p.red, p.paper)
hi("DiffChange", p.gold, p.paper); hi("DiffText", p.fg, p.line)
hi("GitSignsAdd", p.green); hi("GitSignsChange", p.gold); hi("GitSignsDelete", p.red)
hi("ErrorMsg", p.red); hi("WarningMsg", p.gold); hi("Directory", p.blue)
hi("Title", p.fg, nil, {bold=true}); hi("Todo", p.paper, p.fg)
hi("NonText", p.line); hi("EndOfBuffer", p.line, p.bg)
