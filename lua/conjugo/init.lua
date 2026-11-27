-- Conjugo for Neovim: a floating conjugation table for the verb under the cursor.
-- The data comes from `conj --json`; see doc/conjugo.txt.
local M = {}

local LANGS = { fr = true, it = true, es = true, pt = true, en = true, de = true, ru = true }

M.config = {
  cmd = { "conj" }, -- command that runs Conjugo
  default_lang = nil, -- its verbs listed first when spell checking doesn't say (nil: best hit)
  border = "rounded",
  simple = false, -- true: simple tenses only (conj -s)
  glosses = 3, -- glosses shown under the header
  gap = 3, -- spaces between tense columns
  max_width = 0.9, -- fraction of the editor
  max_height = 0.85,
}

local ns = vim.api.nvim_create_namespace("conjugo")

local function set_highlights()
  local links = {
    ConjugoHeader = "Title",
    ConjugoSection = "Statement",
    ConjugoTense = "Identifier",
    ConjugoCompound = "Comment",
    ConjugoPron = "Comment",
    ConjugoMatch = "IncSearch",
    ConjugoInfo = "Special",
    ConjugoGloss = "Normal",
    ConjugoCandidate = "Comment",
    ConjugoCurrent = "Title",
  }
  for group, target in pairs(links) do
    vim.api.nvim_set_hl(0, group, { link = target, default = true })
  end
end

function M.setup(opts)
  M.config = vim.tbl_deep_extend("force", M.config, opts or {})
  set_highlights()
end

-- Guessed language, ranked first but not exclusive: spell checking in one language
-- ('spell' on and a single 'spelllang' entry), else config.default_lang.
-- A list like en,fr,it,pt says nothing.
local function guessed_lang()
  if vim.wo.spell then
    local langs = {}
    for _, entry in ipairs(vim.opt_local.spelllang:get()) do
      local code = entry:sub(1, 2):lower()
      if LANGS[code] and not vim.tbl_contains(langs, code) then
        table.insert(langs, code)
      end
    end
    if #langs == 1 then
      return langs[1]
    end
  end
  return M.config.default_lang
end

-- The word under the cursor, without French elision (j'aime) or hyphenated clitics (levantou-se).
local function current_word()
  local word = vim.fn.expand("<cword>")
  word = vim.fn.substitute(word, [[\v^\a{1,3}['’]\ze\a]], "", "")
  word = vim.fn.substitute(word, [[\v\a\zs-.*$]], "", "")
  return word
end

local function width(s)
  return vim.fn.strdisplaywidth(s)
end

local function pad(s, w)
  return s .. string.rep(" ", w - width(s))
end

-- Lay the data out as lines plus highlight spans {line, col_start, col_end, group} (byte cols).
-- `cands`/`idx`: every candidate verb and which one `data` is (1-based).
local function layout(data, max_width, cands, idx)
  local cfg = M.config
  local lines, spans = {}, {}
  local match = {}
  for _, m in ipairs(data.matches or {}) do
    match[m[1] .. "|" .. tostring(m[2] or vim.NIL)] = true
  end
  local first_match

  local function add(text, group)
    table.insert(lines, text)
    if group then
      table.insert(spans, { #lines - 1, 0, #text, group })
    end
  end

  add(data.header, "ConjugoHeader")
  if data.description ~= "" and vim.fn.tolower(data.query) ~= vim.fn.tolower(data.lemma) then
    add(data.query .. " → " .. data.lemma .. ": " .. data.description, "ConjugoInfo")
  elseif data.description ~= "" then
    add(data.description, "ConjugoInfo")
  end
  -- Candidate line: "2/3  ser · ir · fuir   p/n", the current one highlighted.
  if cands and #cands > 1 then
    local mixed = false
    for _, c in ipairs(cands) do
      mixed = mixed or c.lang ~= cands[1].lang
    end
    local text = idx .. "/" .. #cands .. "  "
    local lnum = #lines
    for i, c in ipairs(cands) do
      if i > 1 then
        text = text .. " · "
      end
      local name = c.lemma .. (mixed and (" (" .. c.lang .. ")") or "")
      if i == idx then
        table.insert(spans, { lnum, #text, #text + #name, "ConjugoCurrent" })
      end
      text = text .. name
    end
    text = text .. "   p/n"
    table.insert(spans, 1, { lnum, 0, #text, "ConjugoCandidate" })
    table.insert(lines, text)
  end
  for i, g in ipairs(data.glosses or {}) do
    if i > cfg.glosses then
      break
    end
    add("  · " .. g, "ConjugoGloss")
  end

  for _, section in ipairs(data.sections) do
    add("")
    add(section.title:upper(), "ConjugoSection")
    -- One column width for the whole section, so the grid lines up.
    local colw = 0
    for _, t in ipairs(section.tenses) do
      colw = math.max(colw, width(t.label))
      for _, c in ipairs(t.cells) do
        colw = math.max(colw, width(c.pron .. c.form))
      end
    end
    local ncols = math.max(1, math.floor((max_width + cfg.gap) / (colw + cfg.gap)))
    for row = 1, #section.tenses, ncols do
      local block = { unpack(section.tenses, row, math.min(row + ncols - 1, #section.tenses)) }
      local height = 0
      for _, t in ipairs(block) do
        height = math.max(height, #t.cells)
      end
      if row > 1 then
        add("")
      end
      for i = 0, height do -- line 0 is the tense label
        local text, lnum = "", #lines
        for j, t in ipairs(block) do
          local sep = j > 1 and string.rep(" ", cfg.gap) or ""
          text = text .. sep
          local start = #text
          if i == 0 then
            text = text .. pad(t.label, colw)
            table.insert(spans, { lnum, start, start + #t.label, t.compound and "ConjugoCompound" or "ConjugoTense" })
          elseif t.cells[i] then
            local c = t.cells[i]
            text = text .. pad(c.pron .. c.form, colw)
            if #c.pron > 0 then
              table.insert(spans, { lnum, start, start + #c.pron, "ConjugoPron" })
            end
            local fs, fe = start + #c.pron, start + #c.pron + #c.form
            if match[t.key .. "|" .. tostring(c.person or vim.NIL)] then
              table.insert(spans, { lnum, fs, fe, "ConjugoMatch" })
              first_match = first_match or { lnum + 1, fs }
            elseif t.compound then
              table.insert(spans, { lnum, fs, fe, "ConjugoCompound" })
            end
          elseif j < #block then
            text = text .. string.rep(" ", colw)
          end
        end
        table.insert(lines, (text:gsub("%s+$", "")))
      end
    end
  end

  -- Spans may run past a line whose trailing spaces were trimmed.
  for _, s in ipairs(spans) do
    s[3] = math.min(s[3], #lines[s[1] + 1])
  end
  return lines, spans, first_match
end

-- Fill `buf` with candidate `idx` and size `win` to it (creating the window if nil).
local function draw(buf, win, cands, idx)
  local cfg = M.config
  local data = cands[idx]
  local max_w = math.floor(vim.o.columns * cfg.max_width) - 2
  local lines, spans, first_match = layout(data, max_w, cands, idx)

  local w = 0
  for _, l in ipairs(lines) do
    w = math.max(w, width(l))
  end
  w = math.min(w + 1, max_w)
  local h = math.min(#lines, math.floor((vim.o.lines - vim.o.cmdheight) * cfg.max_height) - 2)

  vim.bo[buf].modifiable = true
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.api.nvim_buf_clear_namespace(buf, ns, 0, -1)
  for _, sp in ipairs(spans) do
    if sp[3] > sp[2] then
      vim.api.nvim_buf_set_extmark(buf, ns, sp[1], sp[2], { end_col = sp[3], hl_group = sp[4] })
    end
  end
  vim.bo[buf].modifiable = false

  local opts = {
    relative = "editor",
    width = w,
    height = h,
    row = math.floor((vim.o.lines - h) / 2) - 1,
    col = math.floor((vim.o.columns - w) / 2),
    border = cfg.border,
    title = " " .. data.lemma .. " ",
    title_pos = "center",
  }
  if win then
    vim.api.nvim_win_set_config(win, opts)
  else
    opts.style = "minimal"
    win = vim.api.nvim_open_win(buf, true, opts)
    vim.wo[win].wrap = false
    vim.wo[win].cursorline = false
  end

  -- Show the top (header, candidates); scroll only if the match is out of view.
  vim.api.nvim_win_call(win, function()
    vim.fn.winrestview({ topline = 1, lnum = 1, col = 0 })
    vim.api.nvim_win_set_cursor(win, first_match or { 1, 0 })
    if first_match and first_match[1] > h then
      vim.cmd("normal! zz")
    end
  end)
  return win
end

local function open(data)
  -- Older conj versions have no `candidates`: just the one verb.
  local cands = data.candidates or { data }
  local idx = 1
  local buf = vim.api.nvim_create_buf(false, true)
  vim.bo[buf].bufhidden = "wipe"
  vim.bo[buf].filetype = "conjugo"
  local win = draw(buf, nil, cands, idx)

  local function close()
    if vim.api.nvim_win_is_valid(win) then
      vim.api.nvim_win_close(win, true)
    end
  end
  local function step(delta)
    return function()
      if #cands < 2 then
        return
      end
      idx = (idx - 1 + delta) % #cands + 1
      draw(buf, win, cands, idx)
    end
  end
  local map = function(key, fn, desc)
    vim.keymap.set("n", key, fn, { buffer = buf, nowait = true, desc = desc })
  end
  map("q", close, "Close Conjugo")
  map("<Esc>", close, "Close Conjugo")
  map("n", step(1), "Next candidate verb")
  map("p", step(-1), "Previous candidate verb")
  vim.api.nvim_create_autocmd("WinLeave", { buffer = buf, once = true, callback = close })
  return buf, win
end

local function run(word, lang, prefer, on_done)
  local cmd = vim.deepcopy(M.config.cmd)
  table.insert(cmd, "--json")
  if M.config.simple then
    table.insert(cmd, "--simple")
  end
  if prefer then
    vim.list_extend(cmd, { "--prefer", prefer })
  end
  if lang then
    table.insert(cmd, lang)
  end
  table.insert(cmd, word)
  local ok, err = pcall(vim.system, cmd, { text = true }, function(res)
    vim.schedule(function()
      if res.code ~= 0 then
        local msg = vim.trim(res.stderr or "")
        vim.notify("conj failed: " .. (msg ~= "" and msg or ("exit " .. res.code)), vim.log.levels.ERROR)
        return
      end
      local decoded, data = pcall(vim.json.decode, res.stdout)
      if not decoded then
        vim.notify("conj: unreadable output", vim.log.levels.ERROR)
        return
      end
      on_done(data)
    end)
  end)
  if not ok then
    vim.notify("conj: cannot run " .. M.config.cmd[1] .. " (" .. tostring(err) .. ")", vim.log.levels.ERROR)
  end
end

--- Look up a word (default: the word under the cursor) and show its conjugation.
--- opts.lang (or b:conj_lang): fr/it/es/pt/en/de/ru, search only that language. Otherwise
--- search all, the spell-check language (else config.default_lang) first.
--- opts.on_open(buf, win): called after the float opens (used by tests).
function M.lookup(opts)
  opts = opts or {}
  if vim.tbl_isempty(vim.api.nvim_get_hl(0, { name = "ConjugoMatch" })) then
    set_highlights()
  end
  local word = opts.word or current_word()
  if word == "" or not word:find("%a") then
    vim.notify("conj: no word under the cursor", vim.log.levels.WARN)
    return
  end
  -- :Conj {lang} or b:conj_lang restrict the search; a guessed language only ranks.
  local explicit = opts.lang or vim.b.conj_lang
  if explicit and not LANGS[explicit] then
    vim.notify("conj: unknown language " .. explicit, vim.log.levels.ERROR)
    return
  end
  local function done(data)
    if data.found then
      local buf, win = open(data)
      if opts.on_open then
        opts.on_open(buf, win)
      end
    else
      local where = explicit and (" (" .. explicit .. ")") or ""
      vim.notify("conj: '" .. word .. "' is not a verb" .. where, vim.log.levels.WARN)
    end
  end

  if explicit then
    run(word, explicit, nil, done)
  else
    run(word, nil, guessed_lang(), done)
  end
end

return M
