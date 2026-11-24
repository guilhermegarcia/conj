-- Conjugo: :Conj [lang] shows the conjugation of the verb under the cursor.
if vim.g.loaded_conjugo then
  return
end
vim.g.loaded_conjugo = true

vim.api.nvim_create_user_command("Conj", function(args)
  require("conjugo").lookup({ lang = args.fargs[1] })
end, {
  nargs = "?",
  complete = function()
    return { "fr", "it", "es", "pt", "en" }
  end,
  desc = "Conjugo: conjugate the verb under the cursor",
})
