"set mouse=a   enable mouse
set encoding=utf-8
set number
set nobackup
set noswapfile
set nowritebackup                           " only in case you don't want a backup file while editing

set scrolloff=7

set tabstop=4
set softtabstop=4
set shiftwidth=4
set smarttab                                " set tabs for a shifttabs logic
set showtabline=2
set expandtab
set smartindent
set autoindent
set fileformat=unix
"set t_Co=256

set showmatch                               " shows matching part of bracket pairs (), [], {}

filetype indent on      " load filetype-specific indent files

" Options
set shell=/bin/bash
set ttyfast                                 " terminal acceleration

set backspace=indent,eol,start              " backspace removes all (indents, EOLs, start) What is start?

set clipboard+=unnamedplus                  " use system clipboard


" My key bindings
nnoremap <F12> onull=True, blank=True, default=None,<esc>
let mapleader=","


" Install nerd fonts
if !isdirectory(expand("~/.fonts/NerdFonts/"))
    silent !curl --create-dirs -o "${HOME}/.fonts/NerdFonts/mononoki Bold Italic Nerd Font Complete Mono.ttf" "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/patched-fonts/Mononoki/Bold-Italic/complete/mononoki\%20Bold\%20Italic\%20Nerd\%20Font\%20Complete\%20Mono.ttf"
    silent !curl -o "${HOME}/.fonts/NerdFonts/mononoki Bold Italic Nerd Font Complete.ttf" "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/patched-fonts/Mononoki/Bold-Italic/complete/mononoki\%20Bold\%20Italic\%20Nerd\%20Font\%20Complete.ttf"
    silent !curl -o "${HOME}/.fonts/NerdFonts/mononoki Bold Nerd Font Complete Mono.ttf" "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/patched-fonts/Mononoki/Bold/complete/mononoki\%20Bold\%20Nerd\%20Font\%20Complete\%20Mono.ttf"
    silent !curl -o "${HOME}/.fonts/NerdFonts/mononoki Bold Nerd Font Complete.ttf" "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/patched-fonts/Mononoki/Bold/complete/mononoki\%20Bold\%20Nerd\%20Font\%20Complete.ttf"
    silent !curl -o "${HOME}/.fonts/NerdFonts/mononoki Italic Nerd Font Complete Mono.ttf" "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/patched-fonts/Mononoki/Italic/complete/mononoki\%20Italic\%20Nerd\%20Font\%20Complete\%20Mono.ttf"
    silent !curl -o "${HOME}/.fonts/NerdFonts/mononoki Italic Nerd Font Complete.ttf" "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/patched-fonts/Mononoki/Italic/complete/mononoki\%20Italic\%20Nerd\%20Font\%20Complete.ttf"
    silent !curl -o "${HOME}/.fonts/NerdFonts/mononoki-Regular Nerd Font Complete Mono.ttf" "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/patched-fonts/Mononoki/Regular/complete/mononoki-Regular\%20Nerd\%20Font\%20Complete\%20Mono.ttf"
    silent !curl -o "${HOME}/.fonts/NerdFonts/mononoki-Regular Nerd Font Complete.ttf" "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/patched-fonts/Mononoki/Regular/complete/mononoki-Regular\%20Nerd\%20Font\%20Complete.ttf"
    silent !sh -c "cd ~/.fonts; for fontfile in ./NerdFonts/*.ttf; do ln -s \"\$fontfile\"; done"
    silent !fc-cache -f -

    " Reload nvimrc
    source %
endif

" Plug /*
" if !isdirectory(expand("~/.vim/bundle/plug.nvim/"))
if !isdirectory(expand('"${XDG_DATA_HOME:-$HOME/.local/share}/nvim/site/autoload/plug.vim'))

    silent !curl -fLo "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

endif


call plug#begin('~/.vim/plugged')

    Plug 'neovim/nvim-lspconfig'
    Plug 'hrsh7th/nvim-cmp'
    Plug 'hrsh7th/cmp-nvim-lsp'
    Plug 'saadparwaiz1/cmp_luasnip'
    Plug 'L3MON4D3/LuaSnip'

    " color schemas
    Plug 'morhetz/gruvbox'  " colorscheme gruvbox
    " Plug 'mhartington/oceanic-next'  colorscheme OceanicNext
    " Plug 'kaicataldo/material.vim', { 'branch': 'main' }
    " Plug 'ayu-theme/ayu-vim'

    Plug 'preservim/nerdtree'                 " Project and file navigation
    Plug 'Xuyuanp/nerdtree-git-plugin'        " NerdTree git functionality
    Plug 'ryanoasis/vim-devicons'             " Dev Icons

    Plug 'MattesGroeger/vim-bookmarks'        " Bookmarks
    Plug 'thaerkh/vim-indentguides'           " Visual representation of indents
    Plug 'mhinz/vim-startify'                 " Vim Start Page
    Plug 'editorconfig/editorconfig-vim'      " Editorconfig support
    Plug 'Asheq/close-buffers.vim'            " Close buffers
    Plug 'airblade/vim-gitgutter'             " Plugin which shows a git diff in the sign column

    " Bottom line
    Plug 'akinsho/bufferline.nvim'

    " Telescope requirements
    Plug 'nvim-lua/plenary.nvim'
    Plug 'nvim-telescope/telescope.nvim'
    Plug 'nvim-telescope/telescope-fzy-native.nvim'

call plug#end()


colorscheme gruvbox
" colorscheme OceanicNext
"let g:material_terminal_italics = 1
" variants: default, palenight, ocean, lighter, darker, default-community,
"           palenight-community, ocean-community, lighter-community,
"           darker-community
"let g:material_theme_style = 'darker'
"colorscheme material
if (has('termguicolors'))
  set termguicolors
endif

" variants: mirage, dark, dark
"let ayucolor="mirage"
"colorscheme ayu


lua << EOF
-- Set completeopt to have a better completion experience
vim.o.completeopt = 'menuone,noselect'

-- luasnip setup
local luasnip = require 'luasnip'

-- nvim-cmp setup
local cmp = require 'cmp'
cmp.setup {
  completion = {
    autocomplete = false
  },
  snippet = {
    expand = function(args)
      require('luasnip').lsp_expand(args.body)
    end,
  },
  mapping = {
    ['<C-p>'] = cmp.mapping.select_prev_item(),
    ['<C-n>'] = cmp.mapping.select_next_item(),
    ['<C-d>'] = cmp.mapping.scroll_docs(-4),
    ['<C-f>'] = cmp.mapping.scroll_docs(4),
    ['<C-Space>'] = cmp.mapping.complete(),
    ['<C-e>'] = cmp.mapping.close(),
    ['<CR>'] = cmp.mapping.confirm {
      behavior = cmp.ConfirmBehavior.Replace,
      select = true,
    },
    ['<Tab>'] = function(fallback)
      if vim.fn.pumvisible() == 1 then
        vim.fn.feedkeys(vim.api.nvim_replace_termcodes('<C-n>', true, true, true), 'n')
      elseif luasnip.expand_or_jumpable() then
        vim.fn.feedkeys(vim.api.nvim_replace_termcodes('<Plug>luasnip-expand-or-jump', true, true, true), '')
      else
        fallback()
      end
    end,
    ['<S-Tab>'] = function(fallback)
      if vim.fn.pumvisible() == 1 then
        vim.fn.feedkeys(vim.api.nvim_replace_termcodes('<C-p>', true, true, true), 'n')
      elseif luasnip.jumpable(-1) then
        vim.fn.feedkeys(vim.api.nvim_replace_termcodes('<Plug>luasnip-jump-prev', true, true, true), '')
      else
        fallback()
      end
    end,
  },
  sources = {
    { name = 'nvim_lsp' },
    { name = 'luasnip' },
  },
}
EOF




lua << EOF
  local nvim_lsp = require('lspconfig')

  -- Use an on_attach function to only map the following keys
  -- after the language server attaches to the current buffer
  local on_attach = function(client, bufnr)

  local function buf_set_keymap(...) vim.api.nvim_buf_set_keymap(bufnr, ...) end
  local function buf_set_option(...) vim.api.nvim_buf_set_option(bufnr, ...) end

  -- Enable completion triggered by <c-x><c-o>
  buf_set_option('omnifunc', 'v:lua.vim.lsp.omnifunc')

  -- Mappings.
  local opts = { noremap=true, silent=true }

  -- See `:help vim.lsp.*` for documentation on any of the below functions
  buf_set_keymap('n', 'gD', '<cmd>lua vim.lsp.buf.declaration()<CR>', opts)
  buf_set_keymap('n', 'gd', '<cmd>lua vim.lsp.buf.definition()<CR>', opts)
  buf_set_keymap('n', 'K', '<cmd>lua vim.lsp.buf.hover()<CR>', opts)
  buf_set_keymap('n', 'gi', '<cmd>lua vim.lsp.buf.implementation()<CR>', opts)
  buf_set_keymap('n', '<C-k>', '<cmd>lua vim.lsp.buf.signature_help()<CR>', opts)
  buf_set_keymap('n', '<space>wa', '<cmd>lua vim.lsp.buf.add_workspace_folder()<CR>', opts)
  buf_set_keymap('n', '<space>wr', '<cmd>lua vim.lsp.buf.remove_workspace_folder()<CR>', opts)
  buf_set_keymap('n', '<space>wl', '<cmd>lua print(vim.inspect(vim.lsp.buf.list_workspace_folders()))<CR>', opts)
  buf_set_keymap('n', '<space>D', '<cmd>lua vim.lsp.buf.type_definition()<CR>', opts)
  buf_set_keymap('n', '<space>rn', '<cmd>lua vim.lsp.buf.rename()<CR>', opts)
  buf_set_keymap('n', '<space>ca', '<cmd>lua vim.lsp.buf.code_action()<CR>', opts)
  buf_set_keymap('n', 'gr', '<cmd>lua vim.lsp.buf.references()<CR>', opts)
  buf_set_keymap('n', '<space>e', '<cmd>lua vim.lsp.diagnostic.show_line_diagnostics()<CR>', opts)
  buf_set_keymap('n', '[d', '<cmd>lua vim.lsp.diagnostic.goto_prev()<CR>', opts)
  buf_set_keymap('n', ']d', '<cmd>lua vim.lsp.diagnostic.goto_next()<CR>', opts)
  buf_set_keymap('n', '<space>q', '<cmd>lua vim.lsp.diagnostic.set_loclist()<CR>', opts)
  buf_set_keymap('n', '<space>f', '<cmd>lua vim.lsp.buf.formatting()<CR>', opts)

end

-- Use a loop to conveniently call 'setup' on multiple servers and
-- map buffer local keybindings when the language server attaches
local servers = { 'pyright' }
for _, lsp in ipairs(servers) do
  nvim_lsp[lsp].setup {
    on_attach = on_attach,
    flags = {
      debounce_text_changes = 150,
    }
  }
end
EOF



lua << EOF
require("bufferline").setup{}

require("telescope").load_extension("fzy_native")

-- Bottom line
local status, lualine = pcall(require, "lualine")
if (not status) then return end

lualine.setup {
  options = {
    icons_enabled = true,
    theme = 'solarized_dark',
    section_separators = {'', ''},
    component_separators = {'', ''},
    disabled_filetypes = {}
  },
  sections = {
    lualine_a = {'mode'},
    lualine_b = {'branch'},
    lualine_c = {'filename'},
    lualine_x = {
      { 'diagnostics', sources = {"nvim_lsp"}, symbols = {error = ' ', warn = ' ', info = ' ', hint = ' '} },
      'encoding',
      'filetype'
    },
    lualine_y = {'progress'},
    lualine_z = {'location'}
  },
  inactive_sections = {
    lualine_a = {},
    lualine_b = {},
    lualine_c = {'filename'},
    lualine_x = {'location'},
    lualine_y = {},
    lualine_z = {}
  },
  tabline = {},
  extensions = {'fugitive'}
}
-- End bottom line
EOF


" Delete buffer while keeping window layout (don't close buffer's windows).
" Version 2008-11-18 from http://vim.wikia.com/wiki/VimTip165
if v:version < 700 || exists('loaded_bclose') || &cp
  finish
endif
let loaded_bclose = 1
if !exists('bclose_multiple')
  let bclose_multiple = 1
endif

" Display an error message.
function! s:Warn(msg)
  echohl ErrorMsg
  echomsg a:msg
  echohl NONE
endfunction

" Command ':Bclose' executes ':bd' to delete buffer in current window.
" The window will show the alternate buffer (Ctrl-^) if it exists,
" or the previous buffer (:bp), or a blank buffer if no previous.
" Command ':Bclose!' is the same, but executes ':bd!' (discard changes).
" An optional argument can specify which buffer to close (name or number).
function! s:Bclose(bang, buffer)
  if empty(a:buffer)
    let btarget = bufnr('%')
  elseif a:buffer =~ '^\d\+$'
    let btarget = bufnr(str2nr(a:buffer))
  else
    let btarget = bufnr(a:buffer)
  endif
  if btarget < 0
    call s:Warn('No matching buffer for '.a:buffer)
    return
  endif
  if empty(a:bang) && getbufvar(btarget, '&modified')
    call s:Warn('No write since last change for buffer '.btarget.' (use :Bclose!)')
    return
  endif
  " Numbers of windows that view target buffer which we will delete.
  let wnums = filter(range(1, winnr('$')), 'winbufnr(v:val) == btarget')
  if !g:bclose_multiple && len(wnums) > 1
    call s:Warn('Buffer is in multiple windows (use ":let bclose_multiple=1")')
    return
  endif
  let wcurrent = winnr()
  for w in wnums
    execute w.'wincmd w'
    let prevbuf = bufnr('#')
    if prevbuf > 0 && buflisted(prevbuf) && prevbuf != btarget
      buffer #
    else
      bprevious
    endif
    if btarget == bufnr('%')
      " Numbers of listed buffers which are not the target to be deleted.
      let blisted = filter(range(1, bufnr('$')), 'buflisted(v:val) && v:val != btarget')
      " Listed, not target, and not displayed.
      let bhidden = filter(copy(blisted), 'bufwinnr(v:val) < 0')
      " Take the first buffer, if any (could be more intelligent).
      let bjump = (bhidden + blisted + [-1])[0]
      if bjump > 0
        execute 'buffer '.bjump
      else
        execute 'enew'.a:bang
      endif
    endif
  endfor
  execute 'bdelete'.a:bang.' '.btarget
  execute wcurrent.'wincmd w'
endfunction
command! -bang -complete=buffer -nargs=? Bclose call <SID>Bclose(<q-bang>, <q-args>)
nnoremap <silent> <Leader>bd :Bclose<CR>


set colorcolumn=79
setlocal textwidth=79


"=====================================================
"" Tabs / Buffers settings
"=====================================================
tab sball
set switchbuf=useopen
set laststatus=2
set hidden
" switch buffers
nmap <F8> :bp<cr>
nmap <F9> :bn<cr>

" Close current opened buffer
map gw :Bclose<cr>



" close buffers
nnoremap <silent> Q     :Bdelete menu<CR>


"=====================================================
" Bookmarks
highlight BookmarkSign ctermbg=NONE ctermfg=160
highlight BookmarkLine ctermbg=194 ctermfg=NONE
" let g:bookmark_sign = '♥'
let g:bookmark_highlight_lines = 1
"=====================================================


"=====================================================
"" Search settings
"=====================================================
set incsearch	                            " incremental search
set hlsearch	                            " highlight search results

" Find files using Telescope command-line sugar.
nnoremap <leader>ff <cmd>Telescope find_files<cr>
nnoremap <leader>fg <cmd>Telescope live_grep<cr>
nnoremap <leader>fb <cmd>Telescope buffers<cr>
nnoremap <leader>fh <cmd>Telescope help_tags<cr>



"=====================================================
"" NERDTree settings
"=====================================================
let NERDTreeIgnore=['\.pyc$', '\.pyo$', '__pycache__$']     " Ignore files in NERDTree
let NERDTreeWinSize=35
nmap " :NERDTreeToggle<CR>



"=====================================================
"" Git Gutter settings
"=====================================================
nnoremap <leader>gu :GitGutterUndoHunk<cr>


"=====================================================
"" DevIcon Settings
"=====================================================
" loading the plugin
let g:webdevicons_enable = 1

" adding the flags to NERDTree
let g:webdevicons_enable_nerdtree = 1

" turn on/off file node glyph decorations (not particularly useful)
let g:WebDevIconsUnicodeDecorateFileNodes = 1

" use double-width(1) or single-width(0) glyphs
" only manipulates padding, has no effect on terminal or set(guifont) font
let g:WebDevIconsUnicodeGlyphDoubleWidth = 1

" whether or not to show the nerdtree brackets around flags
let g:webdevicons_conceal_nerdtree_brackets = 0

" the amount of space to use after the glyph character (default ' ')
let g:WebDevIconsNerdTreeAfterGlyphPadding = ' '

" Force extra padding in NERDTree so that the filetype icons line up vertically
let g:WebDevIconsNerdTreeGitPluginForceVAlign = 1

" change the default character when no match found
let g:WebDevIconsUnicodeDecorateFileNodesDefaultSymbol = 'ƛ'

" set a byte character marker (BOM) utf-8 symbol when retrieving file encoding
" disabled by default with no value
let g:WebDevIconsUnicodeByteOrderMarkerDefaultSymbol = ''

" enable folder/directory glyph flag (disabled by default with 0)
let g:WebDevIconsUnicodeDecorateFolderNodes = 1

" enable open and close folder/directory glyph flags (disabled by default with 0)
let g:DevIconsEnableFoldersOpenClose = 1

" enable pattern matching glyphs on folder/directory (enabled by default with 1)
let g:DevIconsEnableFolderPatternMatching = 1

" enable file extension pattern matching glyphs on folder/directory (disabled by default with 0)
let g:DevIconsEnableFolderExtensionPatternMatching = 0
