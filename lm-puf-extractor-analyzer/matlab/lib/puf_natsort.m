function [sorted, idx] = puf_natsort(names)
%PUF_NATSORT  Natural-order, case-insensitive sort of a cell array of strings.
%   [SORTED, IDX] = PUF_NATSORT(NAMES) orders NAMES so that embedded numbers
%   compare by value ('S2_rep1' < 'S10_rep1'), as Python's
%   [int(p) if p.isdigit() else p for p in re.split(r'(\d+)', s.lower())] key.

names = names(:);
keys = cell(size(names));
for k = 1:numel(names)
    s = lower(names{k});
    keys{k} = regexprep(s, '\d+', '${sprintf(''%020d'', str2double($0))}');
end
[~, idx] = sort(keys);
sorted = names(idx);
end
