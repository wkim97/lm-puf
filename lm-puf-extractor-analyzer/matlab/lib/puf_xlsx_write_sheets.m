function puf_xlsx_write_sheets(path, sheets)
%PUF_XLSX_WRITE_SHEETS  Write several tables to one .xlsx workbook.
%   PUF_XLSX_WRITE_SHEETS(PATH, SHEETS) where SHEETS is a struct array with
%   fields
%       name   : sheet name
%       table  : a table (written with its variable names as the header row)
%                or a cell array (written as-is, first row = header)
%   Any existing file at PATH is replaced.  On Windows with Excel installed,
%   writetable goes through Excel and leaves the default 'Sheet1..3' in a new
%   workbook; those are removed afterwards so that the first sheet of the
%   file is the first requested sheet (the Python tools and xlsread read the
%   first sheet).

if exist(path, 'file')
    delete(path);
end

warn_state = warning('off', 'MATLAB:xlswrite:AddSheet');
cleanup = onCleanup(@() warning(warn_state));

for k = 1:numel(sheets)
    data = sheets(k).table;
    if iscell(data)
        writetable(cell2table(data), path, 'WriteVariableNames', false, 'Sheet', sheets(k).name);
    else
        writetable(data, path, 'WriteVariableNames', true, 'Sheet', sheets(k).name);
    end
end

remove_default_sheets(path, {sheets.name});
end

function remove_default_sheets(path, keep)
try
    [~, names] = xlsfinfo(path);
catch
    return
end
extra = setdiff(names, keep);
if isempty(extra)
    return
end
% Only Excel itself can delete sheets; skip silently when it is unavailable.
try
    excel = actxserver('Excel.Application');
catch
    return
end
try
    excel.DisplayAlerts = false;
    wb = excel.Workbooks.Open(path);
    for k = 1:numel(extra)
        try
            wb.Worksheets.Item(extra{k}).Delete();
        catch
        end
    end
    wb.Save();
    wb.Close(false);
catch
end
excel.Quit();
delete(excel);
end
