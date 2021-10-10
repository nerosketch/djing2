set mouse=a
set encoding=utf-8
set number
set noswapfile
set scrolloff=7

set tabstop=4
set softtabstop=4
set shiftwidth=4
set expandtab
set autoindent
set fileformat=unix
filetype indent on



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
    source ~/.nvimrc
endif








" Specify a directory for plugins
" - For Neovim: stdpath('data') . '/plugged'
" - Avoid using standard Vim directory names like 'plugin'
call plug#begin('~/.vim/plugged')

    " Make sure you use single quotes

    Plug 'neovim/nvim-lspconfig'
    Plug 'hrsh7th/nvim-cmp'
    Plug 'hrsh7th/cmp-nvim-lsp'
    Plug 'saadparwaiz1/cmp_luasnip'
    Plug 'L3MON4D3/LuaSnip'

    " Color schemas
    Plug 'morhetz/gruvbox'
    "Plug 'mhartington/ocenic-next'
    "Plug 'kaicataldo/material.vim', { 'branch': 'main' }
    "Plug 'ayu-theme/ayu-vim'


    Plug 'preservim/nerdtree'                 " Project and file navigation
    Plug 'Xuyuanp/nerdtree-git-plugin'        " NerdTree git functionality

    Plug 'vim-airline/vim-airline'            " Lean & mean status/tabline for vim
    Plug 'vim-airline/vim-airline-themes'     " Themes for airline
    " Plug 'fisadev/FixedTaskList.vim'          Pending tasks list
    Plug 'MattesGroeger/vim-bookmarks'        " Bookmarks
    Plug 'thaerkh/vim-indentguides'           " Visual representation of indents
    " Plug 'dense-analysis/ale'                 Async Lint Engine
    Plug 'ycm-core/YouCompleteMe'             " Code Completion

    "-------------------=== Other ===-------------------------------
    " Plug 'tpope/vim-surround'                 Parentheses, brackets, quotes, XML tags, and more
    Plug 'flazz/vim-colorschemes'             " Colorschemes
    " Plug 'vimwiki/vimwiki'                     Personal Wiki
    " Plug 'jreybert/vimagit'                   Git Operations
    Plug 'airblade/vim-gitgutter'             " Plug which shows a git diff in the sign column
    Plug 'kien/rainbow_parentheses.vim'       " Rainbow Parentheses
    Plug 'ryanoasis/vim-devicons'             " Dev Icons
    Plug 'mhinz/vim-startify'                 " Vim Start Page
    Plug 'editorconfig/editorconfig-vim'      " Editorconfig support
    Plug 'Asheq/close-buffers.vim'            " Close buffers

    "-------------------=== Snippets support ===--------------------
    "Plug 'garbas/vim-snipmate'                Snippets manager
    "Plug 'MarcWeber/vim-addon-mw-utils'       dependencies #1
    "Plug 'tomtom/tlib_vim'                    dependencies #2
    "Plug 'honza/vim-snippets'                 snippets repo

    "-------------------=== Languages support ===-------------------
    Plug 'preservim/nerdcommenter'           " Easy code documentation
    " Plug 'mitsuhiko/vim-sparkup'             Sparkup(XML/jinja/htlm-django/etc.) support

    "-------------------=== Python  ===-----------------------------
    Plug 'python-mode/python-mode'            " Python mode (docs, refactor, lints...)
    Plug 'hynek/vim-python-pep8-indent'
    Plug 'mitsuhiko/vim-python-combined'
    Plug 'mitsuhiko/vim-jinja'
    Plug 'jmcantrell/vim-virtualenv'






    " Initialize plugin system
call plug#end()

colorscheme gruvbox
" colorscheme OceanicNext

if (has('termguicolors'))
  set termguicolors
endif


filetype on
filetype plugin on
filetype plugin indent on

"=====================================================
"" General settings
"=====================================================
if filereadable(expand("~/.vimrc_background"))
  source ~/.vimrc_background
endif
syntax enable                               " enable syntax highlighting

set pyxversion=0
let g:loaded_python_provider = 1
set shell=/bin/bash
set number                                  " show line numbers
set ruler
set ttyfast                                 " terminal acceleration

set tabstop=4                               " 4 whitespaces for tabs visual presentation
set shiftwidth=4                            " shift lines by 4 spaces
set smarttab                                " set tabs for a shifttabs logic
set expandtab                               " expand tabs into spaces
set autoindent                              " indent when moving to the next line while writing code

set cursorline                              " shows line under the cursor's line
set showmatch                               " shows matching part of bracket pairs (), [], {}

set enc=utf-8	                            " utf-8 by default

set nobackup 	                            " no backup files
set nowritebackup                           " only in case you don't want a backup file while editing
set noswapfile 	                            " no swap files

set backspace=indent,eol,start              " backspace removes all (indents, EOLs, start) What is start?

set scrolloff=10                            " let 10 lines before/after cursor during scroll

set clipboard=unnamed                       " use system clipboard

" set exrc                                    " enable usage of additional .vimrc files from working directory
" set secure                                  " prohibit .vimrc files to execute shell, create files, etc...

"=====================================================
"" Tabs / Buffers settings
"=====================================================
tab sball
set switchbuf=useopen
set laststatus=2
" switch buffers
nmap <F8> :bprev<CR>
nmap <F9> :bnext<CR>
" close buffers
nmap <silent> <leader>q :SyntasticCheck # <CR> :bp <BAR> bd #<CR>
nnoremap <silent> Q     :Bdelete menu<CR>


"=====================================================
" Bookmarks
highlight BookmarkSign ctermbg=NONE ctermfg=160
highlight BookmarkLine ctermbg=194 ctermfg=NONE
" let g:bookmark_sign = '♥'
let g:bookmark_highlight_lines = 1
"=====================================================

"=====================================================
"" YouCompleteMe Settings
"=====================================================
nnoremap gd :YcmCompleter GoTo<CR>

"=====================================================
"" Ale Settings (Linting)
"=====================================================
" Use Ale.
" Show Ale in Airline
let g:airline#extensions#ale#enabled = 1

" Ale Gutter
let g:ale_sign_column_always = 1

"=====================================================
"" Search settings
"=====================================================
set incsearch	                            " incremental search
set hlsearch	                            " highlight search results
noremap <F3> :execute "vimgrep /" . expand("<cword>") . "/j **" <Bar> cw<CR>
noremap <F4> :execute "/" . expand("<cword>") <CR>

" Mouse Cursor enable
" set mouse=a

" Magit open buffer
nnoremap <silent> M :Magit <CR>


"=====================================================
"" Screen scrolling
"=====================================================
noremap <C-Down> j1<C-e>
noremap <C-Up> k1<C-y>

"=====================================================
"" AirLine settings
"=====================================================
let g:airline#extensions#tabline#enabled=1
let g:airline#extensions#tabline#formatter='unique_tail'
let g:airline_powerline_fonts=1
" adding to vim-airline's tabline
let g:webdevicons_enable_airline_tabline = 1
" adding to vim-airline's statusline
let g:webdevicons_enable_airline_statusline = 1
let g:airline#extensions#ale#enabled = 1
let g:airline_theme='wombat'                " set airline theme


"=====================================================
"" TagBar settings
"=====================================================
"let g:tagbar_autofocus=0
"let g:tagbar_width=42
"autocmd BufEnter *.py :call tagbar#autoopen(0)
"autocmd BufWinLeave *.py :TagbarClose

"=====================================================
"" NERDTree settings
"=====================================================
let NERDTreeIgnore=['\.pyc$', '\.pyo$', '__pycache__$']     " Ignore files in NERDTree
let NERDTreeWinSize=35
nmap " :NERDTreeToggle<CR>

"=====================================================
"" NERDComment Settings
"=====================================================
" Add spaces after comment delimiters by default
let g:NERDSpaceDelims = 1

" Use compact syntax for prettified multi-line comments
let g:NERDCompactSexyComs = 1

" Align line-wise comment delimiters flush left instead of following code indentation
let g:NERDDefaultAlign = 'left'

" Set a language to use its alternate delimiters by default
let g:NERDAltDelims_java = 1

" Add your own custom formats or override the defaults
let g:NERDCustomDelimiters = { 'c': { 'left': '/**', 'right': '*/' } }

" Allow commenting and inverting empty lines (useful when commenting a region)
let g:NERDCommentEmptyLines = 1

" Enable trimming of trailing whitespace when uncommenting
let g:NERDTrimTrailingWhitespace = 1


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


"=====================================================
"" SnipMate settings
"=====================================================
let g:snippets_dir='~/.vim/vim-snippets/snippets'
let g:snipMate = get(g:, 'snipMate', {}) " Allow for vimrc re-sourcing
let g:snipMate.snippet_version = 0

"=====================================================
"" Indent Guides Settings
"=====================================================
set listchars=tab:›\ ,trail:•,extends:#,nbsp:.
"=====================================================
"" Python settings
"=====================================================

let g:pymode = 1
let g:pymode_paths = ['./apps']
let g:pymode_trim_whitespaces = 1
setlocal textwidth=119
setlocal commentstring=#\%s
let g:pymode_options_max_line_length=119
let g:syntastic_python_pylint_post_args="--max-line-length=120"

" Autocompletition, and no auto insert first item
set completeopt=menuone,noinsert


" python executables for different plugins
let g:pymode_python='python3'


nmap <leader>g :YcmCompleter GoTo<CR>
nmap <leader>d :YcmCompleter GoToDefinition<CR>

let g:ale_emit_conflict_warnings = 0
let g:pymode_rope_lookup_project = 0

" rope
let g:pymode_rope=0
let g:pymode_rope_completion=0
let g:pymode_rope_complete_on_dot=0
let g:pymode_rope_auto_project=0
let g:pymode_rope_enable_autoimport=0
let g:pymode_rope_autoimport_generate=0
let g:pymode_rope_guess_project=0

" documentation
let g:pymode_doc=0
let g:pymode_doc_bind='K'

" lints
let g:pymode_lint=0

" virtualenv
let g:pymode_virtualenv=1

" breakpoints
let g:pymode_breakpoint=1
let g:pymode_breakpoint_key='<leader>b'

" syntax highlight
let g:pymode_syntax=1
let g:pymode_syntax_slow_sync=1
let g:pymode_syntax_all=1
let g:pymode_syntax_print_as_function=g:pymode_syntax_all
let g:pymode_syntax_highlight_async_await=g:pymode_syntax_all
let g:pymode_syntax_highlight_equal_operator=g:pymode_syntax_all
let g:pymode_syntax_highlight_stars_operator=g:pymode_syntax_all
let g:pymode_syntax_highlight_self=g:pymode_syntax_all
" let g:pymode_syntax_indent_errors=g:pymode_syntax_all
let g:pymode_syntax_string_formatting=g:pymode_syntax_all
let g:pymode_syntax_space_errors=g:pymode_syntax_all
let g:pymode_syntax_string_format=g:pymode_syntax_all
let g:pymode_syntax_string_templates=g:pymode_syntax_all
let g:pymode_syntax_doctests=g:pymode_syntax_all
let g:pymode_syntax_builtin_objs=g:pymode_syntax_all
let g:pymode_syntax_builtin_types=g:pymode_syntax_all
let g:pymode_syntax_highlight_exceptions=g:pymode_syntax_all
let g:pymode_syntax_docstrings=g:pymode_syntax_all

" highlight 'long' lines (>= 119 symbols) in python files
augroup vimrc_autocmds
    autocmd!
    autocmd FileType python,rst,c,cpp highlight Excess ctermbg=DarkGrey guibg=Black
    autocmd FileType python,rst,c,cpp match Excess /\%120v.*/
    autocmd FileType python,rst,c,cpp set nowrap
    autocmd FileType python,rst,c,cpp set colorcolumn=119
augroup END

" code folding
let g:pymode_folding=0

" pep8 indents
let g:pymode_indent=1

" code running
let g:pymode_run=1
let g:pymode_run_bind='<F5>'

let g:ale_sign_column_always = 0
let g:ale_emit_conflict_warnings = 0
let g:pymode_rope_lookup_project = 0

imap <F5> <Esc>:w<CR>:!clear;python %<CR>

" Editorconfig
au FileType gitcommit let b:EditorConfig_disable = 1  " disable for git commits

" Git gutter, diff highlights
highlight GitGutterAdd    guifg=#009900 ctermfg=2
highlight GitGutterChange guifg=#bbbb00 ctermfg=3
highlight GitGutterDelete guifg=#ff2222 ctermfg=1


" no <down> <Nop>
" no <left> <Nop>
" no <right> <Nop>
" no <up> <Nop>

" ino <down> <Nop>
" ino <left> <Nop>
" ino <right> <Nop>
" ino <up> <Nop>

" vno <down> <Nop>
" vno <left> <Nop>
" vno <right> <Nop>
" vno <up> <Nop>


" My Key Bindings

nnoremap <F2> :!git pull<cr>


autocmd StdinReadPre * let g:isReadingFromStdin = 1
autocmd VimEnter * nested if !argc() && !exists('g:isReadingFromStdin') | Startify | endif
autocmd VimEnter * nested if !argc() && !exists('g:isReadingFromStdin') | NERDTree | endif

" Exit Vim if NERDTree is the only window left.
" autocmd BufEnter * if tabpagenr('$') == 1 && winnr('$') == 1 && exists('b:NERDTree') && b:NERDTree.isTabTree() |
"   \ execute :new | endif


" Use the below highlight group when displaying bad whitespace is desired.
highlight BadWhitespace ctermbg=red guibg=red

" Make trailing whitespace be flagged as bad.
au BufRead,BufNewFile *.py,*.pyw,*.c,*.h match BadWhitespace /\s\+$/








" For xml formatting

set redrawtime=10000


function! DoPrettyXML()
  " save the filetype so we can restore it later
  let l:origft = &ft
  set ft=
  " delete the xml header if it exists. This will
  " permit us to surround the document with fake tags
  " without creating invalid xml.
  1s/<?xml .*?>//e
  " insert fake tags around the entire document.
  " This will permit us to pretty-format excerpts of
  " XML that may contain multiple top-level elements.
  0put ='<PrettyXML>'
  $put ='</PrettyXML>'
  silent %!xmllint --nonet --encode utf8 --format -
  " xmllint will insert an <?xml?> header. it's easy enough to delete
  " if you don't want it.
  " delete the fake tags
  2d
  $d
  " restore the 'normal' indentation, which is one extra level
  " too deep due to the extra tags we wrapped around the document.
  silent %<
  " back to home
  1
  " restore the filetype
  exe "set ft=" . l:origft
endfunction
command! PrettyXML call DoPrettyXML()

" com! FormatXML :%!python3 -c "import xml.dom.minidom, sys; print(xml.dom.minidom.parse(sys.stdin).toprettyxml())"
" nnoremap = :FormatXML<Cr>
" nnoremap <F3> :FormatXML<cr>
nnoremap <F6> :PrettyXML<cr>

nnoremap <F12> onull=True, blank=True, default=None,<esc>

