-- Conjugo for Neovim: a floating conjugation table for the verb under the cursor.
-- The data comes from `conj --json`; see doc/conjugo.txt.
local M = {}

local LANGS = { fr = true, it = true, es = true, pt = true, en = true }

M.config = {
  cmd = { "conj" }, -- command that runs Conjugo
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
  }
  for group, target in pairs(links) do
    vim.api.nvim_set_hl(0, group, { link = target, default = true })
  end
end

function M.setup(opts)
  M.config = vim.tbl_deep_extend("force", M.config, opts or {})
  set_highlights()
end

-- Language: explicit argument, then b:conj_lang, then the first 'spelllang' entry.
local function buffer_lang()
  if vim.b.conj_lang and LANGS[vim.b.conj_lang] then
    return vim.b.conj_lang
  end
  for _, entry in ipairs(vim.opt_local.spelllang:get()) do
    local code = entry:sub(1, 2):lower()
    if LANGS[code] then
      return code
    end
  end
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
local function layout(data, max_width)
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

  if data.also and #data.also > 0 then
    add("")
    add("also: " .. table.concat(data.also, ", "), "ConjugoInfo")
  end
  -- Spans may run past a line whose trailing spaces were trimmed.
  for _, s in ipairs(spans) do
    s[3] = math.min(s[3], #lines[s[1] + 1])
  end
  return lines, spans, first_match
end

local function open(data)
  local cfg = M.config
  local max_w = math.floor(vim.o.columns * cfg.max_width) - 2
  local lines, spans, first_match = layout(data, max_w)

  local w = 0
  for _, l in ipairs(lines) do
    w = math.max(w, width(l))
  end
  w = math.min(w + 1, max_w)
  local h = math.min(#lines, math.floor((vim.o.lines - vim.o.cmdheight) * cfg.max_height) - 2)

  local buf = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  for _, s in ipairs(spans) do
    if s[3] > s[2] then
      vim.api.nvim_buf_set_extmark(buf, ns, s[1], s[2], { end_col = s[3], hl_group = s[4] })
    end
  end
  vim.bo[buf].modifiable = false
  vim.bo[buf].bufhidden = "wipe"
  vim.bo[buf].filetype = "conjugo"

  local win = vim.api.nvim_open_win(buf, true, {
    relative = "editor",
    width = w,
    height = h,
    row = math.floor((vim.o.lines - h) / 2) - 1,
    col = math.floor((vim.o.columns - w) / 2),
    style = "minimal",
    border = cfg.border,
    title = " " .. data.lemma .. " ",
    title_pos = "center",
  })
  vim.wo[win].wrap = false
  vim.wo[win].cursorline = false

  if first_match then
    vim.api.nvim_win_set_cursor(win, first_match)
    if first_match[1] > h then
      vim.cmd("normal! zz")
    end
  end

  local function close()
    if vim.api.nvim_win_is_valid(win) then
      vim.api.nvim_win_close(win, true)
    end
  end
  for _, key in ipairs({ "q", "<Esc>" }) do
    vim.keymap.set("n", key, close, { buffer = buf, nowait = true, desc = "Close Conjugo" })
  end
  vim.api.nvim_create_autocmd("WinLeave", { buffer = buf, once = true, callback = close })
  return buf, win
end

local function run(word, lang, on_done)
  local cmd = vim.deepcopy(M.config.cmd)
  table.insert(cmd, "--json")
  if M.config.simple then
    table.insert(cmd, "--simple")
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
--- opts.lang: fr/it/es/pt/en; default b:conj_lang, then 'spelllang', then any language.
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
  local explicit = opts.lang
  if explicit and not LANGS[explicit] then
    vim.notify("conj: unknown language " .. explicit, vim.log.levels.ERROR)
    return
  end
  local lang = explicit or buffer_lang()

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

  run(word, lang, function(data)
    -- A guessed language may be wrong (spelllang=en in a French text): try them all.
    if not data.found and lang and not explicit then
      run(word, nil, done)
    else
      done(data)
    end
  end)
end

return M
