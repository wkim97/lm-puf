function fig = puf_show_results(res, save_dir)
%PUF_SHOW_RESULTS  Dashboard figure of a puf_hd_analysis result.
%   FIG = PUF_SHOW_RESULTS(RES, SAVE_DIR) opens the results window with the
%   six panels of hd_analyzer_min.py ([A] HD distribution, [B] sample-wise
%   intra-HD, [C] normalised Gaussian threshold, [D] per-bit Shannon vs
%   min-entropy, [E] bootstrap convergence, [F] bit-wise uniformity, plus the
%   metrics summary) and a "Save Results (PNG + Excel)" button that writes
%   PUF_Analysis.png / PUF_Analysis.xlsx into SAVE_DIR.

BG = [46 46 46] / 255;
PANEL = [60 63 65] / 255;
mode_intra_only = strcmp(res.analysis_mode, 'intra_only');

intra_hds = res.intra_hds(:);
inter_hds = res.inter_hds(:);

fig = figure('Name', 'PUF Analysis Results', 'NumberTitle', 'off', ...
    'MenuBar', 'none', 'ToolBar', 'none', 'Color', BG, ...
    'Units', 'pixels', 'Position', [60 40 1560 960], 'InvertHardcopy', 'off');

% ---- GridSpec(2, 3, left=0.06, right=0.97, top=0.93, bottom=0.08, hspace=0.44, wspace=0.34)
left = 0.06; right = 0.97; top = 0.93; bottom = 0.08; wspace = 0.34; hspace = 0.44;
cell_w = (right - left) / (3 + 2 * wspace);
gap_w = wspace * cell_w;
cell_h = (top - bottom) / (2 + hspace);
gap_h = hspace * cell_h;
col_x = left + (0:2) * (cell_w + gap_w);
row_y = [bottom + cell_h + gap_h, bottom];          % row 1 = top, row 2 = bottom
plot_frac = 0.955;                                  % bottom 4.5 % of the window is the Save button
to_fig = @(p) [p(1), (1 - plot_frac) + p(2) * plot_frac, p(3), p(4) * plot_frac];

ax_hd = axes('Parent', fig, 'Position', to_fig([col_x(1) row_y(1) cell_w cell_h]));
ax_detail = axes('Parent', fig, 'Position', to_fig([col_x(2) row_y(1) cell_w cell_h]));
sub_h = cell_h / (2 + 0.20); sub_gap = 0.20 * sub_h;
ax_thr_full = axes('Parent', fig, 'Position', to_fig([col_x(3) row_y(1) + sub_h + sub_gap cell_w sub_h]));
ax_thr_zoom = axes('Parent', fig, 'Position', to_fig([col_x(3) row_y(1) cell_w sub_h]));
ax_ent = axes('Parent', fig, 'Position', to_fig([col_x(1) row_y(2) cell_w cell_h]));
sub_h2 = cell_h / (2 + 0.55); sub_gap2 = 0.55 * sub_h2;   % wider gap than matplotlib: MATLAB labels are taller
ax_bs = axes('Parent', fig, 'Position', to_fig([col_x(2) row_y(2) + sub_h2 + sub_gap2 cell_w sub_h2]));
ax_uni = axes('Parent', fig, 'Position', to_fig([col_x(2) row_y(2) cell_w sub_h2]));
ax_sum = axes('Parent', fig, 'Position', to_fig([col_x(3) 0.02 cell_w row_y(1) - 0.09]));   % full column height for the text
all_ax = [ax_hd ax_detail ax_thr_full ax_thr_zoom ax_ent ax_bs ax_uni ax_sum];
for a = all_ax
    style_ax(a, BG);
end

bins = linspace(0, 1, 50);
x_fit = linspace(0, 1, 300);
bin_w = bins(2) - bins(1);

% ---- [A] HD distribution ------------------------------------------------
hold(ax_hd, 'on');
hs = []; labels = {};
if ~isempty(intra_hds)
    h = histogram(ax_hd, intra_hds, 'BinEdges', bins, 'FaceColor', rgb('3a96dd'), 'FaceAlpha', 0.75, 'EdgeColor', 'none');
    hs(end + 1) = h; labels{end + 1} = sprintf('Intra-HD  n=%d', numel(intra_hds));
else
    text(0.5, 0.5, 'No intra-HD pairs available', 'Parent', ax_hd, 'Units', 'normalized', ...
        'HorizontalAlignment', 'center', 'Color', 'w');
end
if ~isempty(inter_hds)
    h = histogram(ax_hd, inter_hds, 'BinEdges', bins, 'FaceColor', rgb('e74c3c'), 'FaceAlpha', 0.75, 'EdgeColor', 'none');
    hs(end + 1) = h; labels{end + 1} = sprintf('Inter-HD  n=%d', numel(inter_hds));
end
if numel(intra_hds) > 1 && isfinite(res.sigma_intra) && res.sigma_intra > 0
    h = plot(ax_hd, x_fit, normpdf(x_fit, res.mu_intra, res.sigma_intra) * numel(intra_hds) * bin_w, ...
        'Color', rgb('7ec8f7'), 'LineWidth', 2);
    hs(end + 1) = h; labels{end + 1} = sprintf('Intra fit %s=%.3f', char(956), res.mu_intra);
end
freeze_y(ax_hd);
if numel(inter_hds) > 1 && isfinite(res.sigma_inter) && res.sigma_inter > 0
    h = plot(ax_hd, x_fit, normpdf(x_fit, res.mu_inter, res.sigma_inter) * numel(inter_hds) * bin_w, ...
        'Color', rgb('f1948a'), 'LineWidth', 2);
    hs(end + 1) = h; labels{end + 1} = sprintf('Inter fit %s=%.3f', char(956), res.mu_inter);
    hs(end + 1) = vline(ax_hd, res.threshold, 'y', '--', 1.2);
    labels{end + 1} = sprintf('Norm. threshold=%.3f', res.threshold);
end
if isfinite(res.fit_cross_x) && ~isclose(res.fit_cross_x, res.threshold)
    hs(end + 1) = vline(ax_hd, res.fit_cross_x, rgb('ff66cc'), '--', 1.2);
    labels{end + 1} = sprintf('Fit intersection=%.3f', res.fit_cross_x);
end
if mode_intra_only
    hs(end + 1) = vline(ax_hd, 0.0, [0.6 0.6 0.6], ':', 1); labels{end + 1} = 'Ideal 0.0';
    title(ax_hd, '[A]  Intra-HD Distribution', 'Color', 'w', 'FontWeight', 'bold', 'Interpreter', 'none');
else
    hs(end + 1) = vline(ax_hd, 0.5, [0.6 0.6 0.6], ':', 1); labels{end + 1} = 'Ideal 0.5';
    title(ax_hd, '[A]  HD Distribution', 'Color', 'w', 'FontWeight', 'bold', 'Interpreter', 'none');
end
xlabel(ax_hd, 'Hamming Distance', 'Color', 'w');
ylabel(ax_hd, 'Count', 'Color', 'w');
add_legend(ax_hd, hs, labels, PANEL, 7, 'northeast');

% ---- [B] Intra-HD detail by sample / pair --------------------------------
hold(ax_detail, 'on');
hs = []; labels = {};
if ~isempty(intra_hds)
    if ~mode_intra_only
        detail_vals = intra_hds;
        detail_labels = cell(size(res.intra_labels));
        for k = 1:numel(res.intra_labels)
            tok = regexp(res.intra_labels{k}, '^S0*(\d+)$', 'tokens', 'once');
            if isempty(tok), detail_labels{k} = res.intra_labels{k}; else detail_labels{k} = ['S' tok{1}]; end
        end
    else
        [detail_vals, order] = sort(intra_hds, 'descend');
        detail_labels = res.intra_labels(order);
    end
    high_th = res.intra_high_threshold;
    is_high = isfinite(high_th) & (detail_vals > high_th);
    x_pos = 0:numel(detail_vals) - 1;
    v_norm = detail_vals; v_norm(is_high) = NaN;
    v_high = detail_vals; v_high(~is_high) = NaN;
    bar(ax_detail, x_pos, v_norm, 0.8, 'FaceColor', rgb('7ec8f7'), 'EdgeColor', 'w', 'LineWidth', 0.3, 'FaceAlpha', 0.88);
    if any(is_high)
        bar(ax_detail, x_pos, v_high, 0.8, 'FaceColor', rgb('ff8c69'), 'EdgeColor', 'w', 'LineWidth', 0.3, 'FaceAlpha', 0.88);
    end
    ylim(ax_detail, [0, max(max(detail_vals) * 1.18, 0.02)]);
    if isfinite(res.mu_intra)
        hs(end + 1) = hline(ax_detail, res.mu_intra, 'w', '--', 1.2);
        labels{end + 1} = sprintf('Mean=%.4f', res.mu_intra);
    end
    if isfinite(high_th)
        hs(end + 1) = hline(ax_detail, high_th, rgb('ffb347'), '--', 1.2);
        labels{end + 1} = sprintf('High guide=%.4f', high_th);
    end
    set(ax_detail, 'XTick', x_pos, 'XTickLabel', detail_labels, 'XTickLabelRotation', 70, 'TickLabelInterpreter', 'none');
    set(ax_detail, 'FontSize', 7);
    if ~mode_intra_only
        xlabel(ax_detail, 'Sample', 'Color', 'w'); ylabel(ax_detail, 'Mean Intra-HD', 'Color', 'w');
    else
        xlabel(ax_detail, 'Pair', 'Color', 'w'); ylabel(ax_detail, 'Intra-HD', 'Color', 'w');
    end
    add_legend(ax_detail, hs, labels, PANEL, 7, 'northeast');
else
    text(0.5, 0.5, 'No intra-HD detail available', 'Parent', ax_detail, 'Units', 'normalized', ...
        'HorizontalAlignment', 'center', 'Color', 'w');
end
if ~mode_intra_only
    title(ax_detail, '[B]  Sample-wise Intra-HD', 'Color', 'w', 'FontWeight', 'bold', 'FontSize', 9, 'Interpreter', 'none');
else
    title(ax_detail, '[B]  Pair-wise Intra-HD', 'Color', 'w', 'FontWeight', 'bold', 'FontSize', 9, 'Interpreter', 'none');
end

% ---- [C] Normalised Gaussian threshold (full + zoom) ----------------------
hold(ax_thr_full, 'on'); hold(ax_thr_zoom, 'on');
if isfinite(res.fit_cross_x)
    x_full = linspace(0, 1, 1200);
    y_intra = normpdf(x_full, res.mu_intra, res.sigma_intra);
    y_inter = normpdf(x_full, res.mu_inter, res.sigma_inter);
    y_full_max = max(max(y_intra), max(y_inter)) * 1.10;
    cross_x = res.fit_cross_x;
    has_cross_y = isfinite(res.fit_cross_y);
    if has_cross_y, cross_y = res.fit_cross_y; else cross_y = 0; end

    hs = []; labels = {};
    hs(end + 1) = plot(ax_thr_full, x_full, y_intra, 'Color', rgb('7ec8f7'), 'LineWidth', 2); labels{end + 1} = 'Intra fit';
    hs(end + 1) = plot(ax_thr_full, x_full, y_inter, 'Color', rgb('f1948a'), 'LineWidth', 2); labels{end + 1} = 'Inter fit';
    xlim(ax_thr_full, [0 1]); ylim(ax_thr_full, [0 y_full_max]);
    if isfinite(res.threshold)
        hs(end + 1) = vline(ax_thr_full, res.threshold, 'y', '--', 1.2);
        labels{end + 1} = sprintf('Norm. threshold=%.4f', res.threshold);
    end
    if has_cross_y
        hs(end + 1) = plot(ax_thr_full, cross_x, cross_y, 'o', 'MarkerSize', 6, 'MarkerFaceColor', rgb('ff66cc'), 'MarkerEdgeColor', 'w');
        labels{end + 1} = 'Intersection';
    end
    ylabel(ax_thr_full, 'Normalized PDF', 'Color', 'w');
    title(ax_thr_full, '[C]  Normalized Gaussian Threshold', 'Color', 'w', 'FontWeight', 'bold', 'FontSize', 9, 'Interpreter', 'none');
    text(0.98, 0.92, sprintf('Threshold = %.4f', res.threshold), 'Parent', ax_thr_full, 'Units', 'normalized', ...
        'HorizontalAlignment', 'right', 'VerticalAlignment', 'top', 'FontSize', 9, 'Color', 'w');
    add_legend(ax_thr_full, hs, labels, PANEL, 7, 'northwest');

    hs = []; labels = {};
    hs(end + 1) = plot(ax_thr_zoom, x_full, y_intra, 'Color', rgb('7ec8f7'), 'LineWidth', 2); labels{end + 1} = 'Intra fit';
    hs(end + 1) = plot(ax_thr_zoom, x_full, y_inter, 'Color', rgb('f1948a'), 'LineWidth', 2); labels{end + 1} = 'Inter fit';
    xlim(ax_thr_zoom, [0.3 0.5]);
    if has_cross_y && cross_y > 0
        y_zoom_max = cross_y * 3.0;
    else
        x_zoom = linspace(0.3, 0.5, 600);
        y_zoom_max = max([max(normpdf(x_zoom, res.mu_intra, res.sigma_intra)), ...
                          max(normpdf(x_zoom, res.mu_inter, res.sigma_inter)), realmin]);
    end
    ylim(ax_thr_zoom, [0 y_zoom_max]);
    if isfinite(res.threshold)
        hs(end + 1) = vline(ax_thr_zoom, res.threshold, 'y', '--', 1.2);
        labels{end + 1} = sprintf('Norm. threshold=%.4f', res.threshold);
    end
    if has_cross_y
        if ~isclose(cross_x, res.threshold)
            hs(end + 1) = vline(ax_thr_zoom, cross_x, rgb('ff66cc'), '--', 1.4);
            labels{end + 1} = sprintf('Intersection=%.4f', cross_x);
        end
        hline(ax_thr_zoom, cross_y, rgb('ff66cc'), ':', 1.0);
        plot(ax_thr_zoom, cross_x, cross_y, 'o', 'MarkerSize', 7, 'MarkerFaceColor', rgb('ff66cc'), 'MarkerEdgeColor', 'w');
    end
    xlabel(ax_thr_zoom, 'Hamming Distance', 'Color', 'w');
    ylabel(ax_thr_zoom, 'Normalized PDF', 'Color', 'w');
    rate_text = sprintf('Normalized threshold = %.4f\nIntersection PDF = %s\nFalse positive rate = %s\nFalse negative rate = %s', ...
        res.threshold, fmt_sci(cross_y), fmt_sci(res.false_positive), fmt_sci(res.false_negative));
    text(0.03, 0.95, rate_text, 'Parent', ax_thr_zoom, 'Units', 'normalized', ...
        'HorizontalAlignment', 'left', 'VerticalAlignment', 'top', 'FontSize', 8.3, 'Color', 'w', ...
        'BackgroundColor', PANEL, 'EdgeColor', [0.4 0.4 0.4], 'Margin', 3, 'Interpreter', 'none');
    add_legend(ax_thr_zoom, hs, labels, PANEL, 7, 'northeast');
else
    if mode_intra_only
        thr_msg = 'Inter-HD fit unavailable in single-sample mode';
    else
        thr_msg = 'Threshold / fit view unavailable';
    end
    for a = [ax_thr_full ax_thr_zoom]
        text(0.5, 0.5, thr_msg, 'Parent', a, 'Units', 'normalized', 'HorizontalAlignment', 'center', 'Color', 'w');
    end
end

% ---- [D] Per-bit Shannon vs min-entropy ----------------------------------
hold(ax_ent, 'on');
hs = []; labels = {};
h = histogram(ax_ent, res.H_bits, 40, 'FaceColor', rgb('f39c12'), 'FaceAlpha', 0.55, 'EdgeColor', 'w', 'LineWidth', 0.3);
hs(end + 1) = h; labels{end + 1} = 'Shannon H_i';
h = histogram(ax_ent, res.hmin_bits_pi, 40, 'FaceColor', rgb('9b59b6'), 'FaceAlpha', 0.55, 'EdgeColor', 'w', 'LineWidth', 0.3);
hs(end + 1) = h; labels{end + 1} = ['Min-ent H' char(8734) '_i'];
freeze_y(ax_ent);
hs(end + 1) = vline(ax_ent, mean(res.H_bits), rgb('f39c12'), '--', 1.8);
labels{end + 1} = sprintf('Shannon avg=%.3f', mean(res.H_bits));
hs(end + 1) = vline(ax_ent, res.hmin_avg_pi, rgb('9b59b6'), '--', 1.8);
labels{end + 1} = sprintf('Min-ent avg=%.3f', res.hmin_avg_pi);
hs(end + 1) = vline(ax_ent, res.hmin_avg_cb, rgb('c39bd3'), '-.', 1.4);
labels{end + 1} = sprintf('Min-ent 99%%LCB=%.3f', res.hmin_avg_cb);
hs(end + 1) = vline(ax_ent, 1.0, [0 1 0], ':', 1.0);
labels{end + 1} = 'Ideal=1.0';
xlabel(ax_ent, 'Per-bit entropy  (bits)', 'Color', 'w');
ylabel(ax_ent, 'Count', 'Color', 'w');
title(ax_ent, '[D]  Per-bit Shannon vs Min-entropy', 'Color', 'w', 'FontWeight', 'bold', 'FontSize', 9, 'Interpreter', 'none');
add_legend(ax_ent, hs, labels, PANEL, 6.2, 'best');

% ---- [E] Bootstrap convergence -------------------------------------------
hold(ax_bs, 'on');
bs = res.bootstrap;
hs = []; labels = {};
has_plot = false;
if ~isempty(bs.ns)
    ns = bs.ns(:)';
    if any(isfinite(bs.inter_means))
        band(ax_bs, ns, bs.inter_means(:)', bs.inter_stds(:)', rgb('e74c3c'), 0.22);
        hs(end + 1) = plot(ax_bs, ns, bs.inter_means, 'Color', rgb('e74c3c'), 'LineWidth', 1.8); labels{end + 1} = 'Inter-HD';
        has_plot = true;
    end
    if any(isfinite(bs.intra_means))
        band(ax_bs, ns, bs.intra_means(:)', bs.intra_stds(:)', rgb('3a96dd'), 0.22);
        hs(end + 1) = plot(ax_bs, ns, bs.intra_means, 'Color', rgb('3a96dd'), 'LineWidth', 1.8); labels{end + 1} = 'Intra-HD';
        has_plot = true;
    end
    if has_plot
        xlim(ax_bs, [ns(1) ns(end)]);
        freeze_y(ax_bs);
        if any(isfinite(bs.inter_means))
            hs(end + 1) = hline(ax_bs, 0.5, [0.7 0.7 0.7], ':', 1); labels{end + 1} = 'Ideal 0.5';
        end
        if isfinite(res.bootstrap_conv_recommended)
            hs(end + 1) = vline(ax_bs, res.bootstrap_conv_recommended, rgb('f1c40f'), '--', 1.2);
            labels{end + 1} = sprintf('Conv. N=%d', round(res.bootstrap_conv_recommended));
        end
        add_legend(ax_bs, hs, labels, PANEL, 6.8, 'best');
    else
        text(0.5, 0.5, 'Bootstrap data unavailable', 'Parent', ax_bs, 'Units', 'normalized', 'HorizontalAlignment', 'center', 'Color', 'w');
    end
    xlabel(ax_bs, 'N samples', 'Color', 'w');
    ylabel(ax_bs, 'Mean HD', 'Color', 'w');
else
    text(0.5, 0.5, 'Bootstrap requires at least 2 samples', 'Parent', ax_bs, 'Units', 'normalized', 'HorizontalAlignment', 'center', 'Color', 'w');
end
title(ax_bs, '[E]  Bootstrap Convergence', 'Color', 'w', 'FontWeight', 'bold', 'FontSize', 8.8, 'Interpreter', 'none');

% ---- [F] Bit-wise uniformity ---------------------------------------------
hold(ax_uni, 'on');
hs = []; labels = {};
p_bits = res.p_bits(:)';
bit_idx = 0:numel(p_bits) - 1;
if ~isempty(bit_idx)
    hs(end + 1) = plot(ax_uni, bit_idx, p_bits, 'Color', rgb('2ecc71'), 'LineWidth', 1.1); labels{end + 1} = 'p(bit=1)';
    fill([bit_idx fliplr(bit_idx)], [p_bits 0.5 * ones(size(p_bits))], rgb('2ecc71'), ...
        'Parent', ax_uni, 'FaceAlpha', 0.10, 'EdgeColor', 'none');
    if numel(bit_idx) > 1, xlim(ax_uni, [0 bit_idx(end)]); else xlim(ax_uni, [0 1]); end
    ylim(ax_uni, [0 1]);
    hs(end + 1) = hline(ax_uni, 0.5, [0.7 0.7 0.7], ':', 1); labels{end + 1} = 'Ideal 0.5';
    hs(end + 1) = hline(ax_uni, mean(p_bits), rgb('f1c40f'), '--', 1.2); labels{end + 1} = sprintf('Mean=%.3f', mean(p_bits));
    add_legend(ax_uni, hs, labels, PANEL, 6.8, 'northeast');
else
    text(0.5, 0.5, 'Bit-wise uniformity unavailable', 'Parent', ax_uni, 'Units', 'normalized', 'HorizontalAlignment', 'center', 'Color', 'w');
end
xlabel(ax_uni, 'Bit index', 'Color', 'w');
ylabel(ax_uni, 'Probability of 1', 'Color', 'w');
title(ax_uni, '[F]  Bit-wise Uniformity', 'Color', 'w', 'FontWeight', 'bold', 'FontSize', 8.8, 'Interpreter', 'none');

% ---- summary --------------------------------------------------------------
axis(ax_sum, 'off');
summary_text = puf_summary_text(res);
text(0.02, 0.97, summary_text, 'Parent', ax_sum, 'Units', 'normalized', ...
    'FontName', 'Consolas', 'FontSize', 5.8, 'VerticalAlignment', 'top', 'Color', 'w', ...
    'BackgroundColor', PANEL, 'EdgeColor', [0.4 0.4 0.4], 'Margin', 4, 'Interpreter', 'none');

if mode_intra_only
    sup = 'LM-PUF  Intra-HD Analysis';
else
    sup = 'LM-PUF  Full PUF Parameter Analysis';
end
annotation(fig, 'textbox', [0 0.955 1 0.04], 'String', sup, 'Color', 'w', 'FontSize', 13, ...
    'FontWeight', 'bold', 'HorizontalAlignment', 'center', 'EdgeColor', 'none', 'Interpreter', 'none');

% ---- Save button ------------------------------------------------------------
uicontrol('Parent', fig, 'Style', 'pushbutton', 'String', 'Save Results  (PNG + Excel)', ...
    'Units', 'normalized', 'Position', [0.013 0.006 0.974 0.036], ...
    'FontName', 'Segoe UI', 'FontSize', 11, 'FontWeight', 'bold', ...
    'BackgroundColor', rgb('e67e22'), 'ForegroundColor', 'w', ...
    'Callback', @(~, ~) on_save());

    function on_save()
        try
            [png_path, xlsx_path] = puf_save_results(fig, res, save_dir);
            [~, pn, pe] = fileparts(png_path);
            [~, xn, xe] = fileparts(xlsx_path);
            msgbox(sprintf('PNG : %s%s\nExcel: %s%s\n\nLocation: %s', pn, pe, xn, xe, save_dir), 'Saved');
        catch err
            errordlg(err.message, 'Error');
        end
    end
end

% ============================================================================
function style_ax(ax, BG)
set(ax, 'Color', BG, 'XColor', 'w', 'YColor', 'w', 'FontSize', 8, 'GridColor', 'w', 'GridAlpha', 0.12, ...
    'TickLabelInterpreter', 'none', 'Box', 'off');
grid(ax, 'on');
end

function c = rgb(hex)
c = [hex2dec(hex(1:2)) hex2dec(hex(3:4)) hex2dec(hex(5:6))] / 255;
end

function s = fmt_sci(x)
if ~isfinite(x), s = 'N/A'; else s = sprintf('%.4e', x); end
end

function tf = isclose(a, b)
tf = abs(a - b) <= 1e-8 + 1e-5 * abs(b);
end

function freeze_y(ax)
yl = get(ax, 'YLim');
set(ax, 'YLim', yl);
end

function h = vline(ax, x, color, style, width)
yl = get(ax, 'YLim');
h = plot(ax, [x x], yl, 'Color', color, 'LineStyle', style, 'LineWidth', width);
set(ax, 'YLim', yl);
end

function h = hline(ax, y, color, style, width)
xl = get(ax, 'XLim');
h = plot(ax, xl, [y y], 'Color', color, 'LineStyle', style, 'LineWidth', width);
set(ax, 'XLim', xl);
end

function band(ax, x, m, s, color, alpha)
ok = isfinite(m) & isfinite(s);
x = x(ok); m = m(ok); s = s(ok);
if isempty(x), return, end
fill([x fliplr(x)], [m - s, fliplr(m + s)], color, 'Parent', ax, 'FaceAlpha', alpha, 'EdgeColor', 'none');
end

function add_legend(ax, hs, labels, PANEL, fontsize, location)
if isempty(hs), return, end
lg = legend(ax, hs, labels, 'Location', location);
set(lg, 'TextColor', 'w', 'Color', PANEL, 'EdgeColor', [0.4 0.4 0.4], 'FontSize', fontsize, 'Interpreter', 'none');
end
