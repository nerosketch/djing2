set nocompatible              " required
filetype off                  " required
set hidden
set showtabline=0


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

    " Reload vimrc
    source ~/.vimrc
endif


" Vundle /*
if !isdirectory(expand("~/.vim/bundle/Vundle.vim/"))
    silent !git clone --depth=1 https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim

    " Reload vimrc
    source ~/.vimrc

    " Directory required for persistent undo history
    if !isdirectory(expand("~/.vim/undodir/"))
        silent !mkdir ~/.vim/undodir/
    endif
endif


" set the runtime path to include Vundle and initialize
set rtp+=~/.vim/bundle/Vundle.vim
call vundle#begin()

    " alternatively, pass a path where Vundle should install plugins
    "call vundle#begin('~/some/path/here')

    " let Vundle manage Vundle, required
    Plugin 'VundleVim/Vundle.vim'                  " Vundle Plugin Manager

    " Add all your plugins here (note older versions of Vundle used Bundle instead of Plugin)
    "-------------------=== Code/Project navigation ===-------------
    Plugin 'preservim/nerdtree'                " Project and file navigation
    Plugin 'Xuyuanp/nerdtree-git-plugin'        " NerdTree git functionality
    Plugin 'majutsushi/tagbar'                  " Class/module browser
    Plugin 'vim-ctrlspace/vim-ctrlspace'        " Tabs/Buffers/Fuzzy/Workspaces/Bookmarks
    Plugin 'mileszs/ack.vim'                    " Ag/Grep
    Plugin 'vim-airline/vim-airline'            " Lean & mean status/tabline for vim
    Plugin 'vim-airline/vim-airline-themes'     " Themes for airline
    Plugin 'fisadev/FixedTaskList.vim'          " Pending tasks list
    Plugin 'yuttie/comfortable-motion.vim'      " Smooth scrolling
    Plugin 'MattesGroeger/vim-bookmarks'        " Bookmarks
    Plugin 'thaerkh/vim-indentguides'           " Visual representation of indents
    Plugin 'dense-analysis/ale'                 " Async Lint Engine
    Plugin 'Valloric/YouCompleteMe'             " Code Completion

    "-------------------=== Other ===-------------------------------
    Plugin 'tpope/vim-surround'                 " Parentheses, brackets, quotes, XML tags, and more
    Plugin 'flazz/vim-colorschemes'             " Colorschemes
    Plugin 'vimwiki/vimwiki'                    " Personal Wiki
    Plugin 'jreybert/vimagit'                   " Git Operations
    Plugin 'kien/rainbow_parentheses.vim'       " Rainbow Parentheses
    Plugin 'ryanoasis/vim-devicons'             " Dev Icons
    Plugin 'mhinz/vim-startify'                 " Vim Start Page
    Plugin 'editorconfig/editorconfig-vim'	    " Editorconfig support

    "-------------------=== Snippets support ===--------------------
    Plugin 'garbas/vim-snipmate'                " Snippets manager
    Plugin 'MarcWeber/vim-addon-mw-utils'       " dependencies #1
    Plugin 'tomtom/tlib_vim'                    " dependencies #2
    Plugin 'honza/vim-snippets'                 " snippets repo

    "-------------------=== Languages support ===-------------------
    Plugin 'preservim/nerdcommenter'           " Easy code documentation
    Plugin 'mitsuhiko/vim-sparkup'              " Sparkup(XML/jinja/htlm-django/etc.) support

    "-------------------=== Python  ===-----------------------------
    Plugin 'python-mode/python-mode'            " Python mode (docs, refactor, lints...)
    Plugin 'hynek/vim-python-pep8-indent'
    Plugin 'mitsuhiko/vim-python-combined'
    Plugin 'mitsuhiko/vim-jinja'
    Plugin 'jmcantrell/vim-virtualenv'

    " All of your Plugins must be added before the following line
call vundle#end()                           " required
filetype on
filetype plugin on
filetype plugin indent on

"=====================================================
"" General settings
"=====================================================
if filereadable(expand("~/.vimrc_background"))
  source ~/.vimrc_background
endif
set encoding=utf-8
set t_Co=256                                " 256 colors
set guifont=mononoki\ Nerd\ Font\ 18
colorscheme wombat256mod                    " set vim colorscheme
let g:airline_theme='wombat'                " set airline theme
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

set scrolloff=20                            " let 10 lines before/after cursor during scroll

set clipboard=unnamed                       " use system clipboard

" set exrc                                    " enable usage of additional .vimrc files from working directory
set secure                                  " prohibit .vimrc files to execute shell, create files, etc...

"=====================================================
"" Tabs / Buffers settings
"=====================================================
tab sball
set switchbuf=useopen
set laststatus=2
nmap <F8> :bprev<CR>
nmap <F9> :bnext<CR>
nmap <silent> <leader>q :SyntasticCheck # <CR> :bp <BAR> bd #<CR>

"=====================================================
"" YouCompleteMe Settings
"=====================================================

"=====================================================
"" Ale Settings (Linting)
"=====================================================
" Use Ale.
" Show Ale in Airline
let g:airline#extensions#ale#enabled = 1

" Ale Gutter
let g:ale_sign_column_always = 1

"=====================================================
"" Relative Numbering
"=====================================================
nnoremap <F4> :set relativenumber!<CR>

"=====================================================
"" Search settings
"=====================================================
set incsearch	                            " incremental search
set hlsearch	                            " highlight search results


" Mouse Cusrsor enable
set mouse=a


"=====================================================
"" Comfortable Motion Settings
"=====================================================
let g:comfortable_motion_scroll_down_key = "j"
let g:comfortable_motion_scroll_up_key = "k"
let g:comfortable_motion_no_default_key_mappings = 1
let g:comfortable_motion_impulse_multiplier = 25  " Feel free to increase/decrease this value.
nnoremap <silent> <C-d> :call comfortable_motion#flick(g:comfortable_motion_impulse_multiplier * winheight(0) * 2)<CR>
nnoremap <silent> <C-u> :call comfortable_motion#flick(g:comfortable_motion_impulse_multiplier * winheight(0) * -2)<CR>
nnoremap <silent> <C-f> :call comfortable_motion#flick(g:comfortable_motion_impulse_multiplier * winheight(0) * 4)<CR>
nnoremap <silent> <C-b> :call comfortable_motion#flick(g:comfortable_motion_impulse_multiplier * winheight(0) * -4)<CR>

"=====================================================
"" AirLine settings
"=====================================================
let g:airline#extensions#tabline#enabled=1
let g:airline#extensions#tabline#formatter='unique_tail'
let g:airline_powerline_fonts=1

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
let NERDTreeWinSize=40
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

" adding to vim-airline's tabline
let g:webdevicons_enable_airline_tabline = 1

" adding to vim-airline's statusline
let g:webdevicons_enable_airline_statusline = 1

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
"" Rainbow Parentheses Autoload
"=====================================================
au VimEnter * RainbowParenthesesToggle
au Syntax * RainbowParenthesesLoadRound
au Syntax * RainbowParenthesesLoadSquare
au Syntax * RainbowParenthesesLoadBraces

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
let g:airline#extensions#ale#enabled = 1
let g:pymode_rope_lookup_project = 0
let g:airline#extensions#tabline#enabled = 1

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
let g:airline#extensions#ale#enabled = 1
let g:pymode_rope_lookup_project = 0
let g:airline#extensions#tabline#enabled = 1

imap <F5> <Esc>:w<CR>:!clear;python %<CR>

" Editorconfig
au FileType gitcommit let b:EditorConfig_disable = 1  " disable for git commits


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


autocmd StdinReadPre * let g:isReadingFromStdin = 1
autocmd VimEnter * nested if !argc() && !exists('g:isReadingFromStdin') | Startify | endif
autocmd VimEnter * nested if !argc() && !exists('g:isReadingFromStdin') | NERDTree | endif

" Exit Vim if NERDTree is the only window left.
autocmd BufEnter * if tabpagenr('$') == 1 && winnr('$') == 1 && exists('b:NERDTree') && b:NERDTree.isTabTree() |
    \ quit | endif

