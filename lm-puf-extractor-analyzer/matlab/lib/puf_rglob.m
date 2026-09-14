function files = puf_rglob(folder, pattern)
%PUF_RGLOB  Recursively list files matching a pattern (e.g. '*.xlsx').
%   FILES = PUF_RGLOB(FOLDER, PATTERN) returns a cell array of full paths of
%   all files under FOLDER (any depth) whose name matches PATTERN.
%   (dir('**/...') is only available from R2016b.)

files = {};
d = dir(fullfile(folder, pattern));
d = d(~[d.isdir]);
for k = 1:numel(d)
    files{end + 1} = fullfile(folder, d(k).name);   %#ok<AGROW>
end

sub = dir(folder);
sub = sub([sub.isdir]);
for k = 1:numel(sub)
    name = sub(k).name;
    if strcmp(name, '.') || strcmp(name, '..')
        continue
    end
    files = [files, puf_rglob(fullfile(folder, name), pattern)];   %#ok<AGROW>
end
end
