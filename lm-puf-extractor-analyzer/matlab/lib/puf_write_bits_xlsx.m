function puf_write_bits_xlsx(path, headers, columns)
%PUF_WRITE_BITS_XLSX  Write the per-window responses to an .xlsx workbook.
%   PUF_WRITE_BITS_XLSX(PATH, HEADERS, COLUMNS) writes one column per
%   temperature window on a single sheet named 'ThermalBits': row 1 holds the
%   window names (e.g. 'R1_40.0-43.0') and the following rows the 1024
%   response bits (row-major flattening of the 32 x 32 matrix).  The layout is
%   identical to the workbook produced by execute.py.

n = numel(columns);
lens = cellfun(@numel, columns);
len = min(lens);                       % Python's zip(*columns) stops at the shortest column

C = cell(len + 1, n);
C(1, :) = headers(:)';
for k = 1:n
    v = double(columns{k});
    C(2:len + 1, k) = num2cell(v(1:len));
end

sheets = struct('name', 'ThermalBits', 'table', {C});
puf_xlsx_write_sheets(path, sheets);
end
