-- Run the real plugin in headless Neovim and dump the float for scripts/nvim_screenshot.py.
-- Usage: see the docstring there.
local COLS, LINES = 112, 36
vim.o.columns, vim.o.lines = COLS, LINES
vim.cmd("colorscheme tokyonight-night")
local conj = require("conjugo")
conj.setup({ default_lang = "fr" })

local text = {
  "# Journal",
  "",
  "Je suis arrivé à Québec hier soir. Je suis fatigué, mais content :",
  "nous parlons déjà de la suite du voyage.",
  "",
  "Demain, on prend le train pour Montréal ; Marie dit qu'elle viendra",
  "avec nous si elle finit son travail à temps.",
  "",
}
vim.api.nvim_buf_set_lines(0, 0, -1, false, text)
vim.api.nvim_win_set_cursor(0, { 3, 4 }) -- on "suis"

local function color(name)
  local h = vim.api.nvim_get_hl(0, { name = name, link = false })
  local function hex(n) return n and string.format("#%06x", n) or nil end
  return { fg = hex(h.fg), bg = hex(h.bg), bold = h.bold or false, italic = h.italic or false }
end

local done = false
conj.lookup({ on_open = function(buf, win)
  local cfg = vim.api.nvim_win_get_config(win)
  local info = vim.fn.getwininfo(win)[1]
  local lines = vim.api.nvim_buf_get_lines(buf, info.topline - 1, info.topline - 1 + cfg.height, false)
  local marks = {}
  for _, m in ipairs(vim.api.nvim_buf_get_extmarks(buf, -1, 0, -1, { details = true })) do
    local r = m[2] - (info.topline - 1)
    if r >= 0 and r < cfg.height then
      table.insert(marks, { r, m[3], m[4].end_col, m[4].hl_group })
    end
  end
  local groups = {}
  for _, g in ipairs({ "Normal", "NormalFloat", "FloatBorder", "FloatTitle", "LineNr", "CursorLineNr",
    "StatusLine", "Title", "ConjugoHeader", "ConjugoSection", "ConjugoTense", "ConjugoCompound",
    "ConjugoPron", "ConjugoMatch", "ConjugoInfo", "ConjugoGloss", "ConjugoCandidate", "ConjugoCurrent" }) do
    groups[g] = color(g)
  end
  local out = {
    cols = COLS, rows = LINES, text = text, cursor = { 3, 4 },
    float = { row = cfg.row, col = cfg.col, width = cfg.width, height = cfg.height,
              title = cfg.title[1][1], lines = lines, marks = marks },
    groups = groups,
  }
  vim.fn.writefile({ vim.json.encode(out) }, vim.env.CONJ_SHOT_OUT or "dump.json")
  done = true
end })
vim.wait(8000, function() return done end)
vim.cmd("qa!")
