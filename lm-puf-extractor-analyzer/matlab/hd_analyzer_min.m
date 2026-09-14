function hd_analyzer_min()
%HD_ANALYZER_MIN  LM-PUF HD & PUF parameter analyzer (min-entropy / NIST SP 800-90B).
%   HD_ANALYZER_MIN() opens the analyzer window.  Select the .xlsx response
%   files of all samples and all repeated measurements (they are natural-
%   sorted and grouped in order: files 1..R = sample 1, R+1..2R = sample 2,
%   ...), set "Reps per sample" and press "Run Full PUF Analysis".  A results
%   window shows the HD distributions, the sample-wise intra-HD, the
%   Gaussian authentication threshold, per-bit Shannon and min-entropy, the
%   convergence of the mean HDs with the number of devices and a metrics
%   summary; "Save Results" writes PUF_Analysis.png and PUF_Analysis.xlsx
%   next to the first selected file.
%
%   MATLAB port of hd_analyzer_min.py.  Tested with MATLAB R2016a.
%   Requires Statistics and Machine Learning Toolbox.

addpath(fullfile(fileparts(mfilename('fullpath')), 'lib'));

BG      = [46 46 46] / 255;
PANEL   = [60 63 65] / 255;
TEXTC   = [1 1 1];
ACCENT  = [58 150 221] / 255;
SUCCESS = [39 174 96] / 255;
ENTRY   = [69 73 74] / 255;
LISTBG  = [43 43 43] / 255;
DISABLED = [127 140 141] / 255;
RUN_TEXT = 'Run Full PUF Analysis  (HD + Uniformity + Uniqueness + Reliability + P_clone + Entropy + Bootstrap)';

script_dir = fileparts(mfilename('fullpath'));
all_files = {};

% ------------------------------------------------------------------ window
fig = figure('Name', 'LM-PUF  HD & PUF Parameter Analyzer  (Min-entropy / NIST SP 800-90B)', ...
    'NumberTitle', 'off', 'MenuBar', 'none', 'ToolBar', 'none', 'Color', BG, ...
    'Units', 'pixels', 'Position', [120 120 980 760]);

% 1. file selection panel
p_file = uipanel('Parent', fig, 'Title', ' 1. Select Excel files (all samples x all reps) ', ...
    'Units', 'pixels', 'BackgroundColor', PANEL, 'ForegroundColor', ACCENT, ...
    'FontName', 'Segoe UI', 'FontSize', 10, 'FontWeight', 'bold', 'HighlightColor', [0.35 0.35 0.35]);
btn_add    = button(p_file, 'Add files', @(~, ~) add_files());
btn_folder = button(p_file, 'Add folder', @(~, ~) add_folder());
btn_test   = button(p_file, 'Load test_data', @(~, ~) load_test_data());
btn_remove = button(p_file, 'Remove selected', @(~, ~) remove_selected());
btn_clear  = button(p_file, 'Clear all', @(~, ~) clear_files());
set(btn_remove, 'Enable', 'off');
lbl_count = uicontrol('Parent', p_file, 'Style', 'text', 'String', '0 files selected', ...
    'HorizontalAlignment', 'right', 'BackgroundColor', PANEL, 'ForegroundColor', ACCENT, ...
    'FontName', 'Segoe UI', 'FontSize', 10, 'FontWeight', 'bold');
listbox = uicontrol('Parent', p_file, 'Style', 'listbox', 'String', {}, 'Min', 0, 'Max', 2, 'Value', [], ...
    'BackgroundColor', LISTBG, 'ForegroundColor', TEXTC, 'FontName', 'Consolas', 'FontSize', 9, ...
    'Callback', @(~, ~) update_remove_button(), 'KeyPressFcn', @on_list_key);

% 2. settings panel
p_cfg = uipanel('Parent', fig, 'Title', ' 2. Settings ', 'Units', 'pixels', ...
    'BackgroundColor', PANEL, 'ForegroundColor', ACCENT, 'FontName', 'Segoe UI', 'FontSize', 10, ...
    'FontWeight', 'bold', 'HighlightColor', [0.35 0.35 0.35]);
label(p_cfg, 'Reps per sample:', [12 40 110 20]);
edit_rep = uicontrol('Parent', p_cfg, 'Style', 'edit', 'String', '5', 'Position', [125 40 50 24], ...
    'BackgroundColor', ENTRY, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 10, ...
    'Callback', @(~, ~) refresh_info());
uicontrol('Parent', p_cfg, 'Style', 'pushbutton', 'String', '+', 'Position', [178 52 20 13], ...
    'FontSize', 7, 'Callback', @(~, ~) step_rep(1));
uicontrol('Parent', p_cfg, 'Style', 'pushbutton', 'String', '-', 'Position', [178 39 20 13], ...
    'FontSize', 7, 'Callback', @(~, ~) step_rep(-1));
label(p_cfg, 'Detected samples:', [235 40 120 20]);
lbl_samples = uicontrol('Parent', p_cfg, 'Style', 'text', 'String', '0', 'Position', [360 39 60 22], ...
    'HorizontalAlignment', 'left', 'BackgroundColor', PANEL, 'ForegroundColor', [0 1 0.53], ...
    'FontName', 'Segoe UI', 'FontSize', 11, 'FontWeight', 'bold');
uicontrol('Parent', p_cfg, 'Style', 'text', 'Position', [12 10 700 20], ...
    'String', 'Files are grouped in order: files 1~N = sample1, N+1~2N = sample2 ...', ...
    'HorizontalAlignment', 'left', 'BackgroundColor', PANEL, 'ForegroundColor', [0.67 0.67 0.67], ...
    'FontName', 'Segoe UI', 'FontSize', 10);

% 3. run button
btn_run = uicontrol('Parent', fig, 'Style', 'pushbutton', 'String', RUN_TEXT, 'Units', 'pixels', ...
    'BackgroundColor', DISABLED, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', 'FontSize', 11, ...
    'FontWeight', 'bold', 'Enable', 'off', 'Callback', @(~, ~) run_analysis());

layout();
set(fig, 'ResizeFcn', @(~, ~) layout());

% ------------------------------------------------------------------ layout
    function layout()
        if ~ishandle(fig), return, end
        pos = get(fig, 'Position');
        W = pos(3); H = pos(4);
        m = 15;
        run_h = 50; cfg_h = 90;
        set(btn_run, 'Position', [m, 10, W - 2 * m, run_h]);
        set(p_cfg, 'Position', [m, 10 + run_h + 10, W - 2 * m, cfg_h]);
        file_y = 10 + run_h + 10 + cfg_h + 5;
        file_h = max(H - file_y - m, 120);
        set(p_file, 'Position', [m, file_y, W - 2 * m, file_h]);
        pw = W - 2 * m; ph = file_h;
        x = 10; bw = [80 90 110 125 80]; y_btn = ph - 55;
        hs = [btn_add, btn_folder, btn_test, btn_remove, btn_clear];
        for k = 1:5
            set(hs(k), 'Position', [x, y_btn, bw(k), 28]);
            x = x + bw(k) + 6;
        end
        set(lbl_count, 'Position', [pw - 260, y_btn + 2, 245, 22]);
        set(listbox, 'Position', [10, 10, pw - 20, max(y_btn - 20, 40)]);
    end

% ------------------------------------------------------------------ files
    function refresh_file_listbox()
        items = cell(numel(all_files), 1);
        root_dir = [pwd filesep];
        for k = 1:numel(all_files)
            f = all_files{k};
            if strncmpi(f, root_dir, numel(root_dir))
                display = f(numel(root_dir) + 1:end);
            else
                [~, n, e] = fileparts(f);
                display = [n e];
            end
            items{k} = ['  ' display];
        end
        set(listbox, 'String', items, 'Value', []);
    end

    function update_remove_button()
        if isempty(get(listbox, 'Value'))
            set(btn_remove, 'Enable', 'off');
        else
            set(btn_remove, 'Enable', 'on');
        end
    end

    function added = add_paths(paths)
        added = 0;
        for k = 1:numel(paths)
            p = paths{k};
            if ~any(strcmp(all_files, p))
                all_files{end + 1} = p;   %#ok<AGROW>
                added = added + 1;
            end
        end
        all_files = puf_natsort(all_files);
        all_files = all_files(:)';
        refresh_file_listbox();
        refresh_info();
        if isempty(all_files)
            set(btn_run, 'Enable', 'off', 'BackgroundColor', DISABLED);
        else
            set(btn_run, 'Enable', 'on', 'BackgroundColor', SUCCESS);
        end
        update_remove_button();
    end

    function add_files()
        [names, folder] = uigetfile({'*.xlsx', 'Excel files (*.xlsx)'; '*.*', 'All files (*.*)'}, ...
            'Select xlsx files (all samples, all reps)', 'MultiSelect', 'on');
        if isequal(names, 0), return, end
        if ischar(names), names = {names}; end
        paths = cellfun(@(n) fullfile(folder, n), names, 'UniformOutput', false);
        added = add_paths(paths);
        if added == 0
            msgbox('No new Excel files were added.', 'Info');
        end
    end

    function add_folder()
        folder = uigetdir(pwd, 'Select folder containing xlsx files');
        if isequal(folder, 0), return, end
        files = puf_rglob(folder, '*.xlsx');
        if isempty(files)
            warndlg('No .xlsx files were found in the selected folder.', 'No Files');
            return
        end
        added = add_paths(files);
        set(lbl_count, 'String', sprintf('%d files selected (%d added)', numel(all_files), added));
    end

    function load_test_data()
        test_dir = fullfile(script_dir, 'test_data');
        if ~exist(test_dir, 'dir')
            errordlg(sprintf('Folder not found:\n%s', test_dir), 'Missing Folder');
            return
        end
        files = puf_rglob(test_dir, '*.xlsx');
        if isempty(files)
            warndlg(sprintf('No .xlsx files were found under:\n%s', test_dir), 'No Files');
            return
        end
        added = add_paths(files);
        set(lbl_count, 'String', sprintf('%d files selected (%d added)', numel(all_files), added));
    end

    function clear_files()
        all_files = {};
        set(listbox, 'String', {}, 'Value', []);
        set(lbl_count, 'String', '0 files selected');
        set(lbl_samples, 'String', '0');
        set(btn_run, 'Enable', 'off', 'BackgroundColor', DISABLED);
        update_remove_button();
    end

    function remove_selected()
        sel = get(listbox, 'Value');
        sel = sel(sel >= 1 & sel <= numel(all_files));
        if isempty(sel), return, end
        first_index = min(sel);
        all_files(sel) = [];
        removed = numel(sel);
        refresh_file_listbox();
        refresh_info();
        set(lbl_count, 'String', sprintf('%d files selected (%d removed)', numel(all_files), removed));
        if isempty(all_files)
            set(btn_run, 'Enable', 'off', 'BackgroundColor', DISABLED);
        else
            set(btn_run, 'Enable', 'on', 'BackgroundColor', SUCCESS);
            set(listbox, 'Value', min(first_index, numel(all_files)));
        end
        update_remove_button();
    end

    function on_list_key(~, evt)
        if any(strcmp(evt.Key, {'delete', 'backspace'}))
            remove_selected();
        end
    end

    function n_rep = get_n_rep()
        n_rep = round(str2double(get(edit_rep, 'String')));
        if ~isfinite(n_rep) || n_rep < 1, n_rep = 1; end
        if n_rep > 100, n_rep = 100; end
        set(edit_rep, 'String', num2str(n_rep));
    end

    function step_rep(delta)
        set(edit_rep, 'String', num2str(max(1, min(100, get_n_rep() + delta))));
        refresh_info();
    end

    function refresh_info()
        n_rep = get_n_rep();
        n_files = numel(all_files);
        set(lbl_count, 'String', sprintf('%d files selected', n_files));
        set(lbl_samples, 'String', num2str(floor(n_files / n_rep)));
    end

% ------------------------------------------------------------------ analysis
    function run_analysis()
        n_rep = get_n_rep();
        n_files = numel(all_files);
        n_samples = floor(n_files / n_rep);
        n_leftover = mod(n_files, n_rep);
        if n_samples < 1
            errordlg(sprintf('File count (%d) < reps per sample (%d).', n_files, n_rep), 'Error');
            return
        end
        if n_leftover
            uiwait(warndlg(sprintf(['File count (%d) is not divisible by reps per sample (%d).\n' ...
                '%d file(s) at the end will be ignored.'], n_files, n_rep, n_leftover), 'Warning'));
        end
        if n_samples == 1 && n_rep < 2
            errordlg('Single-sample intra-HD analysis requires at least 2 repetitions.', 'Error');
            return
        end
        if n_samples < 2
            uiwait(warndlg('Only 1 sample selected. Inter-HD based metrics will be skipped.', 'Warning'));
        end
        set(btn_run, 'Enable', 'off', 'String', 'Computing...');
        drawnow;
        try
            res = puf_hd_analysis(all_files, n_rep, @(msg) fprintf('>> %s\n', msg));
            save_dir = fileparts(all_files{1});
            puf_show_results(res, save_dir);
        catch err
            fprintf(2, '%s\n', getReport(err, 'extended', 'hyperlinks', 'off'));
            errordlg(err.message, 'Error');
        end
        if ishandle(btn_run)
            set(btn_run, 'Enable', 'on', 'String', RUN_TEXT);
        end
    end

% ------------------------------------------------------------------ helpers
    function h = button(parent, str, cb)
        h = uicontrol('Parent', parent, 'Style', 'pushbutton', 'String', str, ...
            'BackgroundColor', ACCENT, 'ForegroundColor', TEXTC, 'FontName', 'Segoe UI', ...
            'FontSize', 10, 'FontWeight', 'bold', 'Callback', cb);
    end

    function h = label(parent, str, pos)
        h = uicontrol('Parent', parent, 'Style', 'text', 'String', str, 'Position', pos, ...
            'HorizontalAlignment', 'left', 'BackgroundColor', PANEL, 'ForegroundColor', TEXTC, ...
            'FontName', 'Segoe UI', 'FontSize', 10);
    end
end
