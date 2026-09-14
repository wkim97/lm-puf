function txt = puf_summary_text(res)
%PUF_SUMMARY_TEXT  Fixed-width metrics summary shown in the results dashboard.
%   TXT = PUF_SUMMARY_TEXT(RES) formats the metrics of a puf_hd_analysis
%   result exactly like the summary panel of hd_analyzer_min.py.

mode_intra_only = strcmp(res.analysis_mode, 'intra_only');
intra_hds = res.intra_hds(:);
inter_hds = res.inter_hds(:);

intra_mean = safe_mean(intra_hds);
intra_std = safe_std(intra_hds);
inter_mean = safe_mean(inter_hds);
inter_std = safe_std(inter_hds);
if mode_intra_only
    intra_entry_ideal = '-';
    mode_str = 'Intra-only';
else
    intra_entry_ideal = sprintf('%d', res.n_samples);
    mode_str = 'Full';
end
worst_label = 'N/A';
worst_value = NaN;
if ~isempty(intra_hds)
    [worst_value, k] = max(intra_hds);
    worst_label = res.intra_labels{k};
end

sep = repmat('-', 1, 46);
L = {};
L{end + 1} = sep;
L{end + 1} = sprintf('  LM-PUF Standard Metrics (N=%d devices, %d bits)', res.n_samples, res.n_bits);
L{end + 1} = sep;
L{end + 1} = row('Metric', 'Value', 'Ideal');
L{end + 1} = sep;
L{end + 1} = row('Analysis mode', mode_str, '-');
L{end + 1} = row('Intra-HD entries', sprintf('%d', numel(intra_hds)), intra_entry_ideal);
L{end + 1} = row('Uniformity', fmt_value(res.uniformity * 100, 3, '%'), '50.000%');
L{end + 1} = row('Uniqueness', fmt_value(res.uniqueness, 3, '%'), '100.000%');
L{end + 1} = row('Reliability', fmt_value(res.reliability, 3, '%'), '100.000%');
L{end + 1} = sep;
L{end + 1} = row('Intra-HD  mean', fmt_value(intra_mean, 4, ''), '0.0000');
L{end + 1} = row('Intra-HD  std', fmt_value(intra_std, 4, ''), '');
L{end + 1} = row('Inter-HD  mean', fmt_value(inter_mean, 4, ''), '0.5000');
L{end + 1} = row('Inter-HD  std', fmt_value(inter_std, 4, ''), '');
L{end + 1} = sep;
L{end + 1} = row('Fit intersection', fmt_value(res.fit_cross_x, 4, ''), '');
L{end + 1} = row('Auth threshold (norm. PDF)', fmt_value(res.threshold, 4, ''), '');
L{end + 1} = row('Legacy threshold (3-sigma)', fmt_value(res.threshold_legacy, 4, ''), '');
L{end + 1} = row('False positive rate', fmt_sci(res.false_positive), '');
L{end + 1} = row('False negative rate', fmt_sci(res.false_negative), '');
L{end + 1} = row('P_clone  log10', log10_safe(res.p_clone), '<< -30');
L{end + 1} = row(sprintf('Collision (N=%d)  log10', res.n_samples), log10_safe(res.collision), '<<  0');
L{end + 1} = sep;
L{end + 1} = row('Bootstrap conv. N inter', fmt_value(res.bootstrap_conv_inter, 0, ''), '');
L{end + 1} = row('Bootstrap conv. N intra', fmt_value(res.bootstrap_conv_intra, 0, ''), '');
L{end + 1} = row('Bootstrap conv. N rec.', fmt_value(res.bootstrap_conv_recommended, 0, ''), '');
L{end + 1} = sep;
L{end + 1} = row('Shannon H_avg (bits/bit, UB)', fmt_value(res.H_avg, 4, ''), '1.0000');
L{end + 1} = row('Shannon H_total (=H_avg*Nb)', fmt_value(res.H_total, 1, ''), sprintf('%.0f', res.n_bits));
L{end + 1} = row('IBR  (%)', fmt_value(res.IBR, 3, '%'), '100.000%');
L{end + 1} = sep;
L{end + 1} = row('MIN-ENTROPY (NIST 800-90B)', '', 'ideal/bit');
L{end + 1} = row('  Min-ent/bit (plug-in)', fmt_value(res.hmin_avg_pi, 4, ''), '1.0000');
L{end + 1} = row('  Min-ent/bit (99% LCB, n=dev)', fmt_value(res.hmin_avg_cb, 4, ''), '1.0000');
L{end + 1} = row('  Min-ent total (sum = UB)', fmt_value(res.hmin_total_pi, 1, ''), sprintf('%.0f', res.n_bits));
L{end + 1} = row('  NIST MCV/bit (IID, pooled)', fmt_value(res.nist_hmin, 4, ''), '1.0000');
L{end + 1} = row('  NIST MCV p_max (upper)', fmt_value(res.nist_pu, 4, ''), '0.5000');
if mode_intra_only
    L{end + 1} = sep;
    L{end + 1} = '  Note: inter-HD based metrics are unavailable in single-sample mode.';
end
if ~isempty(intra_hds)
    L{end + 1} = sep;
    L{end + 1} = sprintf('  Worst intra target: %s = %s', worst_label, fmt_value(worst_value, 4, ''));
    if isfinite(res.intra_high_threshold)
        L{end + 1} = sprintf('  High intra guide: mean + 2%s = %s', char(963), fmt_value(res.intra_high_threshold, 4, ''));
    end
end
L{end + 1} = sep;
L{end + 1} = '  Caveat: ''total'' entropy = sum of per-bit values, which is an';
L{end + 1} = '  UPPER bound on joint entropy (equality iff bits independent).';
L{end + 1} = '  Use min-entropy (lower bound) for cryptographic keyspace claims;';
L{end + 1} = '  for keyspace, derive effective DoF from the inter-HD distribution.';
L{end + 1} = sep;

txt = strjoin(L, sprintf('\n'));
end

function s = row(metric, value, ideal)
if isempty(ideal)
    s = sprintf('  %-28s  %10s', metric, value);
else
    s = sprintf('  %-28s  %10s  %10s', metric, value, ideal);
end
end

function s = fmt_value(x, digits, suffix)
if ~isfinite(x)
    s = 'N/A';
else
    s = sprintf(['%.' num2str(digits) 'f%s'], x, suffix);
end
end

function s = fmt_sci(x)
if ~isfinite(x), s = 'N/A'; else s = sprintf('%.4e', x); end
end

function s = log10_safe(x)
if isnan(x)
    s = 'N/A';
elseif x <= 0
    s = '-inf';
else
    s = sprintf('%.1f', log10(x));
end
end

function m = safe_mean(v)
if isempty(v), m = NaN; else m = mean(v); end
end

function s = safe_std(v)
if isempty(v), s = NaN; else s = std(v, 1); end
end
