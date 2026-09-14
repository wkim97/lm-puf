function res = puf_hd_analysis(files, n_rep, progress_fn)
%PUF_HD_ANALYSIS  Full PUF figure-of-merit analysis of a set of response files.
%   RES = PUF_HD_ANALYSIS(FILES, N_REP) loads the .xlsx response files FILES
%   (cell array, already in the desired order), groups them in order as
%   files 1..N_REP = sample 1, N_REP+1..2*N_REP = sample 2, ... and computes
%     - intra-device HD (all repetition pairs of a sample) and inter-device HD
%       (first repetition of every pair of samples),
%     - uniformity, uniqueness, reliability (Maiti et al. 2013),
%     - Gaussian fits, their intersection, the authentication threshold,
%       false positive / negative rates, P_clone and the expected number of
%       collisions (Pal et al. 2022),
%     - per-bit Shannon entropy (upper bound) and NIST SP 800-90B min-entropy
%       (per-bit plug-in, 99 % lower confidence bound, IID most-common-value),
%     - a random-subsampling convergence analysis of the mean HDs versus the
%       number of devices (200 subsets without replacement per n).
%   RES = PUF_HD_ANALYSIS(FILES, N_REP, PROGRESS_FN) calls PROGRESS_FN(MSG)
%   with status strings while running.
%
%   Port of HDAnalyzerGUI._run_analysis and the metric functions of
%   hd_analyzer_min.py.  Requires Statistics and Machine Learning Toolbox
%   (normpdf / normcdf / norminv).

if nargin < 3 || isempty(progress_fn), progress_fn = @(msg) []; end

n_rep = max(1, round(n_rep));
n_files = numel(files);
n_samples = floor(n_files / n_rep);
if n_samples < 1
    error('puf:hd', 'File count (%d) < reps per sample (%d).', n_files, n_rep);
end
if n_samples == 1 && n_rep < 2
    error('puf:hd', 'Single-sample intra-HD analysis requires at least 2 repetitions.');
end

% ---- load ---------------------------------------------------------------
progress_fn('Loading files...');
names = cell(n_samples, 1);
samples = cell(n_samples, 1);
for i = 1:n_samples
    names{i} = sprintf('S%02d', i);
    reps = cell(n_rep, 1);
    for j = 1:n_rep
        idx = (i - 1) * n_rep + j;
        reps{j} = puf_read_bits_xlsx(files{idx});
        [~, fn, fe] = fileparts(files{idx});
        fprintf('   [%s rep%d] %s%s\n', names{i}, j, fn, fe);
    end
    samples{i} = reps;
end

% ---- intra-HD -----------------------------------------------------------
progress_fn('Computing intra-HD...');
intra_hds = [];
intra_labels = {};
intra_pair_rows = struct('sample', {}, 'pair', {}, 'hd', {});
intra_sample_stats = struct('sample', {}, 'n_pairs', {}, 'mean', {}, 'std', {}, 'min', {}, 'max', {});
intra_sum = zeros(n_samples, 1);
intra_cnt = zeros(n_samples, 1);
for i = 1:n_samples
    reps = samples{i};
    pairwise = [];
    pair_labels = {};
    for a = 1:n_rep
        for b = a + 1:n_rep
            hd = hamming(reps{a}, reps{b});
            pairwise(end + 1) = hd;                                          %#ok<AGROW>
            pair_labels{end + 1} = sprintf('%s_rep%d_vs_rep%d', names{i}, a, b); %#ok<AGROW>
            intra_pair_rows(end + 1) = struct('sample', names{i}, ...
                'pair', sprintf('rep%d_vs_rep%d', a, b), 'hd', hd);         %#ok<AGROW>
        end
    end
    if isempty(pairwise)
        continue
    end
    intra_sum(i) = sum(pairwise);
    intra_cnt(i) = numel(pairwise);
    st = struct('sample', names{i}, 'n_pairs', numel(pairwise), ...
        'mean', mean(pairwise), 'std', std(pairwise, 1), ...
        'min', min(pairwise), 'max', max(pairwise));
    intra_sample_stats(end + 1) = st;                                        %#ok<AGROW>
    if n_samples == 1
        intra_hds = [intra_hds; pairwise(:)];                                %#ok<AGROW>
        intra_labels = [intra_labels, pair_labels];                          %#ok<AGROW>
    else
        intra_hds(end + 1) = st.mean;                                        %#ok<AGROW>
        intra_labels{end + 1} = names{i};                                    %#ok<AGROW>
    end
end
intra_hds = intra_hds(:);
intra_labels = intra_labels(:);

% ---- inter-HD -----------------------------------------------------------
progress_fn('Computing inter-HD...');
D = zeros(n_samples, n_samples);
inter_hds = [];
inter_labels = {};
for a = 1:n_samples
    for b = a + 1:n_samples
        hd = hamming(samples{a}{1}, samples{b}{1});
        D(a, b) = hd;
        D(b, a) = hd;
        inter_hds(end + 1) = hd;                                             %#ok<AGROW>
        inter_labels{end + 1} = sprintf('%s_vs_%s', names{a}, names{b});    %#ok<AGROW>
    end
end
inter_hds = inter_hds(:);
inter_labels = inter_labels(:);

intra_mean_global = safe_mean(intra_hds);
intra_std_global = safe_std(intra_hds);
intra_high_threshold = NaN;
if numel(intra_hds) > 1 && isfinite(intra_std_global) && intra_std_global > 0
    intra_high_threshold = intra_mean_global + 2.0 * intra_std_global;
end
% rank the samples by mean intra-HD (descending), z-score them, flag outliers
means = [intra_sample_stats.mean];
means_sort = means;
means_sort(~isfinite(means_sort)) = -Inf;
[~, order] = sort(means_sort, 'descend');
intra_sample_stats = intra_sample_stats(order);
for r = 1:numel(intra_sample_stats)
    m_r = intra_sample_stats(r).mean;
    if isfinite(intra_std_global) && intra_std_global > 0 && isfinite(m_r)
        z = (m_r - intra_mean_global) / intra_std_global;
    else
        z = NaN;
    end
    intra_sample_stats(r).rank = r;
    intra_sample_stats(r).zscore = z;
    intra_sample_stats(r).is_high_outlier = isfinite(intra_high_threshold) && m_r > intra_high_threshold;
end

% ---- bit matrix (rep 1 of every sample) ---------------------------------
min_len = min(cellfun(@(s) numel(s{1}), samples));
bits_mat = zeros(n_samples, min_len);
for i = 1:n_samples
    v = samples{i}{1};
    bits_mat(i, :) = v(1:min_len)';
end

% ---- PUF metrics --------------------------------------------------------
progress_fn('Computing PUF metrics...');
res = struct();
res.files = files(:);
res.names = names;
res.samples = samples;
res.n_samples = n_samples;
res.n_rep = n_rep;
if n_samples == 1
    res.analysis_mode = 'intra_only';
else
    res.analysis_mode = 'full';
end
res.n_bits = min_len;
res.intra_hds = intra_hds;
res.intra_labels = intra_labels;
res.inter_hds = inter_hds;
res.inter_labels = inter_labels;
res.intra_pair_rows = intra_pair_rows;
res.intra_sample_stats = intra_sample_stats;
res.intra_high_threshold = intra_high_threshold;

res.uniformity = mean(bits_mat(:));                                  % Maiti 2013, ideal 0.5
res.uniqueness = uniqueness(inter_hds);
res.reliability = reliability(intra_hds);

[res.H_total, res.H_avg, res.IBR, res.p_bits, res.H_bits] = shannon_entropy(bits_mat);
[res.hmin_total_pi, res.hmin_avg_pi, res.hmin_total_cb, res.hmin_avg_cb, ...
    res.hmin_bits_pi, res.hmin_bits_cb] = min_entropy_perbit(bits_mat, 0.005);
[res.nist_hmin, res.nist_phat, res.nist_pu, res.nist_n] = nist_mcv_min_entropy(bits_mat, 0.005);

[res.mu_inter, res.sigma_inter] = gaussian_stats(inter_hds);
res.mu_intra = safe_mean(intra_hds);
res.sigma_intra = safe_std(intra_hds);
[res.fit_cross_x, res.fit_cross_y] = gaussian_intersection(res.mu_intra, res.sigma_intra, res.mu_inter, res.sigma_inter);
res.threshold_legacy = NaN;
if isfinite(res.mu_inter) && isfinite(res.sigma_inter)
    res.threshold_legacy = res.mu_inter - 3.0 * res.sigma_inter;
end
if isfinite(res.fit_cross_x)
    res.threshold = res.fit_cross_x;
else
    res.threshold = res.threshold_legacy;
end
[res.false_positive, res.false_negative] = false_rates(res.mu_intra, res.sigma_intra, res.mu_inter, res.sigma_inter, res.threshold);
res.p_clone = res.false_positive;
res.collision = collision_prob(res.p_clone, n_samples);

% ---- convergence vs. number of devices ("bootstrap") --------------------
progress_fn('Bootstrap convergence (B=200, please wait)...');
res.bootstrap = bootstrap_convergence(D, intra_sum, intra_cnt, 200);
res.bootstrap_conv_inter = convergence_n(res.bootstrap.ns, res.bootstrap.inter_means, res.bootstrap.inter_stds, 0.005, 0.005);
res.bootstrap_conv_intra = convergence_n(res.bootstrap.ns, res.bootstrap.intra_means, res.bootstrap.intra_stds, 0.005, 0.005);
if isfinite(res.bootstrap_conv_inter) && isfinite(res.bootstrap_conv_intra)
    res.bootstrap_conv_recommended = max(res.bootstrap_conv_inter, res.bootstrap_conv_intra);
elseif isfinite(res.bootstrap_conv_inter)
    res.bootstrap_conv_recommended = res.bootstrap_conv_inter;
elseif isfinite(res.bootstrap_conv_intra)
    res.bootstrap_conv_recommended = res.bootstrap_conv_intra;
else
    res.bootstrap_conv_recommended = NaN;
end
progress_fn('Done.');
end

% =========================================================================
%  metric helpers (Maiti 2013, Pal 2022, Shannon 1948, NIST SP 800-90B)
% =========================================================================
function hd = hamming(a, b)
n = min(numel(a), numel(b));
hd = sum(a(1:n) ~= b(1:n)) / n;
end

function m = safe_mean(v)
if isempty(v), m = NaN; else m = mean(v); end
end

function s = safe_std(v)
if isempty(v), s = NaN; else s = std(v, 1); end        % population std (numpy default)
end

function u = uniqueness(inter_hds)
% Uniqueness = 2/(q(q-1)) * sum(HD_ij / s) * 100 % = 2 * mean(inter HD) * 100 %
if isempty(inter_hds), u = NaN; else u = 2.0 * mean(inter_hds) * 100.0; end
end

function r = reliability(intra_hds)
% Reliability = (1 - mean intra HD) * 100 %
if isempty(intra_hds), r = NaN; else r = (1.0 - mean(intra_hds)) * 100.0; end
end

function [mu, sigma] = gaussian_stats(hds)
if numel(hds) < 2, mu = NaN; sigma = NaN; else mu = mean(hds); sigma = std(hds, 1); end
end

function [fpr, fnr] = false_rates(mu_intra, sigma_intra, mu_inter, sigma_inter, threshold)
% FPR = P(inter <= threshold), FNR = P(intra > threshold) from the Gaussian fits
vals = [mu_intra, sigma_intra, mu_inter, sigma_inter, threshold];
if ~all(isfinite(vals)) || sigma_intra <= 0 || sigma_inter <= 0
    fpr = NaN; fnr = NaN;
    return
end
fpr = normcdf(threshold, mu_inter, sigma_inter);
fnr = normcdf(threshold, mu_intra, sigma_intra, 'upper');
end

function c = collision_prob(p_clone, n_devices)
% Expected number of collisions among n devices: C(n,2) * P_clone
if n_devices < 2 || ~isfinite(p_clone), c = NaN; else c = nchoosek(n_devices, 2) * p_clone; end
end

function [x, y] = gaussian_intersection(mu1, sigma1, mu2, sigma2)
% Intersection of two normalised Gaussian PDFs; prefers the root between the means.
x = NaN; y = NaN;
if ~all(isfinite([mu1, sigma1, mu2, sigma2])) || sigma1 <= 0 || sigma2 <= 0
    return
end
if abs(sigma1 - sigma2) <= 1e-8 + 1e-5 * abs(sigma2)         % numpy.isclose
    x = 0.5 * (mu1 + mu2);
    y = normpdf(x, mu1, sigma1);
    return
end
a = 1 / sigma1^2 - 1 / sigma2^2;
b = -2 * mu1 / sigma1^2 + 2 * mu2 / sigma2^2;
c = mu1^2 / sigma1^2 - mu2^2 / sigma2^2 - 2 * log(sigma2 / sigma1);
r = roots([a, b, c]);
r = sort(real(r(imag(r) == 0)));
if isempty(r)
    return
end
lo = min(mu1, mu2);
hi = max(mu1, mu2);
between = r(r >= lo & r <= hi);
if ~isempty(between)
    x = between(1);
else
    [~, k] = min(abs(r - 0.5 * (mu1 + mu2)));
    x = r(k);
end
y = normpdf(x, mu1, sigma1);
end

function [H_total, H_avg, IBR, p, H] = shannon_entropy(bits_mat)
% Per-bit Shannon entropy across devices (ideal 1 bit / bit); summing it is an upper bound.
eps_ = 1e-12;
p = mean(bits_mat, 1);
p_s = min(max(p, eps_), 1 - eps_);
H = -p_s .* log2(p_s) - (1 - p_s) .* log2(1 - p_s);
H_total = sum(H);
H_avg = mean(H);
IBR = H_total / size(bits_mat, 2) * 100.0;
end

function [Hmin_total_pi, Hmin_avg_pi, Hmin_total_cb, Hmin_avg_cb, Hmin_bits_pi, Hmin_bits_cb] = min_entropy_perbit(bits_mat, alpha)
% Per-bit min-entropy H_inf = -log2(max(p, 1-p)); plug-in and NIST-style 99 % lower confidence bound.
eps_ = 1e-12;
N = size(bits_mat, 1);
p = mean(bits_mat, 1);
pmax = min(max(max(p, 1 - p), 0.5), 1 - eps_);
Hmin_bits_pi = -log2(pmax);
if N > 1
    z = norminv(1 - alpha);
    pmax_u = min(1 - eps_, pmax + z * sqrt(pmax .* (1 - pmax) / (N - 1)));
else
    pmax_u = pmax;
end
Hmin_bits_cb = -log2(pmax_u);
Hmin_total_pi = sum(Hmin_bits_pi);
Hmin_avg_pi = mean(Hmin_bits_pi);
Hmin_total_cb = sum(Hmin_bits_cb);
Hmin_avg_cb = mean(Hmin_bits_cb);
end

function [H_min, p_hat, p_u, n] = nist_mcv_min_entropy(bits_mat, alpha)
% NIST SP 800-90B IID most-common-value estimator on the pooled bit stream.
eps_ = 1e-12;
flat = bits_mat(:);
n = numel(flat);
if n < 2
    H_min = NaN; p_hat = NaN; p_u = NaN;
    return
end
c1 = sum(flat ~= 0);
p_hat = max(n - c1, c1) / n;
z = norminv(1 - alpha);
p_u = min(1 - eps_, p_hat + z * sqrt(p_hat * (1 - p_hat) / (n - 1)));
H_min = -log2(p_u);
end

function bs = bootstrap_convergence(D, intra_sum, intra_cnt, B)
% For n = 2..N draw B random subsets of n devices (without replacement) and
% record mean +/- std of the mean inter-HD (all pairs among the subset, rep 1)
% and of the mean intra-HD (all repetition pairs of the subset's devices).
N = size(D, 1);
bs = struct('ns', [], 'inter_means', [], 'inter_stds', [], 'intra_means', [], 'intra_stds', []);
if N < 2
    return
end
ns = 2:N;
bs.ns = ns;
bs.inter_means = nan(size(ns));
bs.inter_stds = nan(size(ns));
bs.intra_means = nan(size(ns));
bs.intra_stds = nan(size(ns));
for k = 1:numel(ns)
    n = ns(k);
    inter_b = zeros(B, 1);
    intra_b = zeros(B, 1);
    has_intra = false(B, 1);
    for b = 1:B
        chosen = randperm(N, n);
        sub = D(chosen, chosen);
        inter_b(b) = mean(sub(triu(true(n), 1)));
        cnt = sum(intra_cnt(chosen));
        if cnt > 0
            intra_b(b) = sum(intra_sum(chosen)) / cnt;
            has_intra(b) = true;
        end
    end
    bs.inter_means(k) = mean(inter_b);
    bs.inter_stds(k) = std(inter_b, 1);
    if any(has_intra)
        bs.intra_means(k) = mean(intra_b(has_intra));
        bs.intra_stds(k) = std(intra_b(has_intra), 1);
    end
end
end

function n_conv = convergence_n(ns, means, stds, mean_tol, std_tol)
% Smallest n after which the mean stays within mean_tol of the final mean and
% the std stays below std_tol (heuristic convergence point).
n_conv = NaN;
if isempty(ns) || isempty(means) || isempty(stds)
    return
end
finite_mask = isfinite(means) & isfinite(stds);
if ~any(finite_mask)
    return
end
fm = means(finite_mask);
final_mean = fm(end);
for i = 1:numel(ns)
    tail_means = means(i:end);
    tail_stds = stds(i:end);
    tm = isfinite(tail_means) & isfinite(tail_stds);
    if ~any(tm)
        continue
    end
    if all(abs(tail_means(tm) - final_mean) <= mean_tol) && all(tail_stds(tm) <= std_tol)
        n_conv = ns(i);
        return
    end
end
end
