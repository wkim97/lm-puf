function out = puf_names(op, file_path)
%PUF_NAMES  File-name conventions shared by the extractor tools.
%   PUF_NAMES('strip_generated', STEM)  removes a trailing '_new' / '_reduced'.
%   PUF_NAMES('strip_repeat', STEM)     removes a trailing repeat index
%                                       (' 3', '_3', '-3').
%   PUF_NAMES('is_long_term', STEM)     true when the stem contains 'long term'
%                                       / 'long_term' / 'longterm'.
%   PUF_NAMES('group_name', PATH)       shared point-group name of a *_new.mat
%                                       file ('Longterm' for long-term runs).
%   PUF_NAMES('group_key', PATH)        lower-case <dir>/<group_name>, used to
%                                       decide which files share points/ROI.
%   PUF_NAMES('points_path', PATH)      <dir>/<group>_points.mat
%   PUF_NAMES('group_roi_path', PATH)   <dir>/<group>_roi.mat
%   PUF_NAMES('common_roi_path', PATH)  <dir>/common_roi.mat
%   PUF_NAMES('is_target', PATH)        true for *_new.mat files
%   PUF_NAMES('base_name', PATH)        stem with '_new' / '_reduced' removed
%                                       (output-folder prefix)
%   PUF_NAMES('sm_group_key', PATH)     samplematcher grouping key
%                                       (<dir>/<stem without repeat index>)
%   PUF_NAMES('sm_is_generated', PATH)  true for *_xy.mat / *_new.mat
%   PUF_NAMES('xy_path', PATH)          <dir>/<stem>_xy.mat
%   PUF_NAMES('new_path', PATH)         <dir>/<stem>_new.mat
%
%   Mirrors the helper methods of execute.py and samplematcher.py.

switch op
    case 'strip_generated'
        out = strip_generated(file_path);
    case 'strip_repeat'
        out = strip_repeat(file_path);
    case 'is_long_term'
        out = is_long_term(file_path);
    case 'group_name'
        out = group_name(file_path);
    case 'group_key'
        d = fileparts(file_path);
        out = fullfile(lower(d), lower(group_name(file_path)));
    case 'points_path'
        d = fileparts(file_path);
        out = fullfile(d, [group_name(file_path) '_points.mat']);
    case 'group_roi_path'
        d = fileparts(file_path);
        out = fullfile(d, [group_name(file_path) '_roi.mat']);
    case 'common_roi_path'
        d = fileparts(file_path);
        out = fullfile(d, 'common_roi.mat');
    case 'is_target'
        [~, stem, ext] = fileparts(file_path);
        out = strcmpi(ext, '.mat') && ends_with(lower(stem), '_new');
    case 'base_name'
        [~, stem] = fileparts(file_path);
        out = strrep(strrep(stem, '_new', ''), '_reduced', '');
    case 'sm_group_key'
        [d, stem] = fileparts(file_path);
        out = fullfile(lower(d), lower(strip_repeat(stem)));
    case 'sm_is_generated'
        [~, stem] = fileparts(file_path);
        s = lower(stem);
        out = ends_with(s, '_xy') || ends_with(s, '_new');
    case 'xy_path'
        [d, stem] = fileparts(file_path);
        out = fullfile(d, [stem '_xy.mat']);
    case 'new_path'
        [d, stem] = fileparts(file_path);
        out = fullfile(d, [stem '_new.mat']);
    otherwise
        error('puf:names', 'Unknown operation: %s', op);
end
end

function tf = ends_with(s, suffix)
tf = numel(s) >= numel(suffix) && strcmp(s(end - numel(suffix) + 1:end), suffix);
end

function stem = strip_generated(stem)
suffixes = {'_new', '_reduced'};
for k = 1:numel(suffixes)
    if ends_with(lower(stem), suffixes{k})
        stem = stem(1:end - numel(suffixes{k}));
    end
end
end

function stem = strip_repeat(stem)
stem = regexprep(stem, '(?:[ _-])\d+$', '');
end

function tf = is_long_term(stem)
tf = ~isempty(regexpi(stem, '(^|[_ -])long[_ -]?term($|[_ -])', 'once'));
end

function name = group_name(file_path)
[~, stem] = fileparts(file_path);
stem = strip_repeat(strip_generated(stem));
if is_long_term(stem)
    name = 'Longterm';
else
    name = stem;
end
end
