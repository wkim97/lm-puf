function [png_path, xlsx_path] = puf_save_results(fig, res, save_dir)
%PUF_SAVE_RESULTS  Write the dashboard PNG and the PUF_Analysis.xlsx workbook.
%   [PNG, XLSX] = PUF_SAVE_RESULTS(FIG, RES, SAVE_DIR) saves FIG as
%   PUF_Analysis.png (150 dpi) and the metrics of RES as PUF_Analysis.xlsx
%   with the sheets PUF_Metrics, Intra_HD_values, Intra_HD_by_sample,
%   Intra_HD_pairs, Inter_HD_raw (when available), Bootstrap and
%   Per_bit_entropy - the same layout as hd_analyzer_min.py.

png_path = fullfile(save_dir, 'PUF_Analysis.png');
xlsx_path = fullfile(save_dir, 'PUF_Analysis.xlsx');

% ---- PNG ----
set(fig, 'InvertHardcopy', 'off', 'PaperPositionMode', 'auto');
print(fig, png_path, '-dpng', '-r150', '-noui');

% ---- Excel ----
intra_hds = res.intra_hds(:);
inter_hds = res.inter_hds(:);
intra_mean = safe_mean(intra_hds);
intra_std = safe_std(intra_hds);
inter_mean = safe_mean(inter_hds);
inter_std = safe_std(inter_hds);
if isfinite(res.p_clone) && res.p_clone > 0
    p_clone_log10 = round(log10(res.p_clone), 2);
else
    p_clone_log10 = 'N/A';
end
dash = repmat(char(9472), 1, 20);
dash10 = repmat(char(9472), 1, 10);
mode_full = strcmp(res.analysis_mode, 'full');
if mode_full
    intra_entry_ideal = res.n_samples;
    mode_str = 'Full';
else
    intra_entry_ideal = '-';
    mode_str = 'Intra-only';
end

metrics = {
    'Metric', 'Value', 'Ideal', 'Reference';
    'N_samples', res.n_samples, '-', '-';
    'N_bits per response', res.n_bits, '-', '-';
    'N_reps per sample', res.n_rep, '-', '-';
    'Intra-HD entries', numel(intra_hds), intra_entry_ideal, '-';
    'Analysis mode', mode_str, '-', '-';
    dash, dash10, dash10, dash;
    'Uniformity (%)', excel_scalar(res.uniformity * 100, 4), 50.0, 'Maiti et al. 2013';
    'Uniqueness (%)', excel_scalar(res.uniqueness, 4), 100.0, 'Maiti et al. 2013';
    'Reliability (%)', excel_scalar(res.reliability, 4), 100.0, 'Maiti et al. 2013';
    dash, dash10, dash10, dash;
    'Intra-HD mean', excel_scalar(intra_mean, 6), 0.0, '-';
    'Intra-HD std', excel_scalar(intra_std, 6), '-', '-';
    'Inter-HD mean', excel_scalar(inter_mean, 6), 0.5, '-';
    'Inter-HD std', excel_scalar(inter_std, 6), '-', '-';
    dash, dash10, dash10, dash;
    'Fit intersection', excel_scalar(res.fit_cross_x, 4), '-', '-';
    'Auth threshold (norm. PDF)', excel_scalar(res.threshold, 4), '-', '-';
    'Legacy threshold (3-sigma)', excel_scalar(res.threshold_legacy, 4), '-', 'Pal et al. 2022';
    'False positive rate', excel_scalar(res.false_positive, []), '-', '-';
    'False negative rate', excel_scalar(res.false_negative, []), '-', '-';
    'P_clone', excel_scalar(res.p_clone, []), '<< 1', 'Pal et al. 2022';
    'P_clone log10', p_clone_log10, '<<-30', 'Pal et al. 2022';
    sprintf('Collision E[N=%d]', res.n_samples), excel_scalar(res.collision, []), '<< 1', '-';
    dash, dash10, dash10, dash;
    'Bootstrap conv. N inter', excel_scalar(res.bootstrap_conv_inter, []), '-', '-';
    'Bootstrap conv. N intra', excel_scalar(res.bootstrap_conv_intra, []), '-', '-';
    'Bootstrap conv. N rec.', excel_scalar(res.bootstrap_conv_recommended, []), '-', '-';
    dash, dash10, dash10, dash;
    'Shannon H_avg (bits/bit, UB)', excel_scalar(res.H_avg, 6), 1.0, 'Shannon 1948 (uniformity / upper bound)';
    'Shannon H_total (=H_avg*Nbits)', excel_scalar(res.H_total, 4), res.n_bits, 'subadditive UPPER bound, not keyspace';
    'IBR (%)', excel_scalar(res.IBR, 4), 100.0, 'Kim et al. 2025';
    dash, dash10, dash10, dash;
    'Min-entropy/bit (plug-in)', excel_scalar(res.hmin_avg_pi, 6), 1.0, 'NIST SP 800-90B (2018)';
    'Min-entropy/bit (99% LCB)', excel_scalar(res.hmin_avg_cb, 6), 1.0, 'NIST SP 800-90B (n = N_devices)';
    'Min-entropy total (sum, UB)', excel_scalar(res.hmin_total_pi, 4), res.n_bits, 'subadditive UPPER bound, not keyspace';
    'NIST MCV min-ent/bit (IID)', excel_scalar(res.nist_hmin, 6), 1.0, 'NIST SP 800-90B IID-MCV (pooled)';
    'NIST MCV p_max (upper)', excel_scalar(res.nist_pu, 6), 0.5, 'NIST SP 800-90B';
    'NIST MCV pooled n (bits)', excel_scalar(res.nist_n, []), '-', 'NIST SP 800-90B';
    };

sheets = struct('name', {}, 'table', {});
sheets(end + 1) = struct('name', 'PUF_Metrics', 'table', {metrics});

C = [{'Sample_or_pair', 'HD'}; [res.intra_labels(:), num2cell(round(intra_hds, 6))]];
sheets(end + 1) = struct('name', 'Intra_HD_values', 'table', {C});

st = res.intra_sample_stats;
C = cell(numel(st) + 1, 9);
C(1, :) = {'Sample', 'Mean_HD', 'Std_HD', 'Min_HD', 'Max_HD', 'N_pairs', 'Rank', 'Zscore', 'High_outlier'};
for r = 1:numel(st)
    if st(r).is_high_outlier, flag = 'Y'; else flag = ''; end
    C(r + 1, :) = {st(r).sample, excel_scalar(st(r).mean, 6), excel_scalar(st(r).std, 6), ...
        excel_scalar(st(r).min, 6), excel_scalar(st(r).max, 6), st(r).n_pairs, st(r).rank, ...
        excel_scalar(st(r).zscore, 4), flag};
end
sheets(end + 1) = struct('name', 'Intra_HD_by_sample', 'table', {C});

pr = res.intra_pair_rows;
C = cell(numel(pr) + 1, 3);
C(1, :) = {'Sample', 'Pair', 'HD'};
for r = 1:numel(pr)
    C(r + 1, :) = {pr(r).sample, pr(r).pair, round(pr(r).hd, 6)};
end
sheets(end + 1) = struct('name', 'Intra_HD_pairs', 'table', {C});

if ~isempty(inter_hds)
    C = [{'Pair', 'HD'}; [res.inter_labels(:), num2cell(round(inter_hds, 6))]];
    sheets(end + 1) = struct('name', 'Inter_HD_raw', 'table', {C});
end

bs = res.bootstrap;
C = cell(numel(bs.ns) + 1, 5);
C(1, :) = {'N_samples', 'Inter_HD_mean', 'Inter_HD_std', 'Intra_HD_mean', 'Intra_HD_std'};
for r = 1:numel(bs.ns)
    C(r + 1, :) = {bs.ns(r), blank_nan(bs.inter_means(r)), blank_nan(bs.inter_stds(r)), ...
        blank_nan(bs.intra_means(r)), blank_nan(bs.intra_stds(r))};
end
sheets(end + 1) = struct('name', 'Bootstrap', 'table', {C});

nb = numel(res.p_bits);
C = cell(nb + 1, 5);
C(1, :) = {'Bit_index', 'p_i', 'H_shannon_i', 'Hmin_i', 'Hmin_i_99LCB'};
C(2:end, 1) = num2cell((0:nb - 1)');
C(2:end, 2) = num2cell(round(res.p_bits(:), 6));
C(2:end, 3) = num2cell(round(res.H_bits(:), 6));
C(2:end, 4) = num2cell(round(res.hmin_bits_pi(:), 6));
C(2:end, 5) = num2cell(round(res.hmin_bits_cb(:), 6));
sheets(end + 1) = struct('name', 'Per_bit_entropy', 'table', {C});

puf_xlsx_write_sheets(xlsx_path, sheets);
fprintf('>> Saved: %s\n>> Saved: %s\n', png_path, xlsx_path);
end

function v = excel_scalar(x, digits)
if ischar(x)
    v = x;
elseif ~isfinite(x)
    v = 'N/A';
elseif isempty(digits)
    v = double(x);
else
    v = round(double(x), digits);
end
end

function v = blank_nan(x)
if isnan(x), v = ''; else v = round(x, 6); end
end

function m = safe_mean(v)
if isempty(v), m = NaN; else m = mean(v); end
end

function s = safe_std(v)
if isempty(v), s = NaN; else s = std(v, 1); end
end
