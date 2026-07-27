function stage07_multipath_validation_matlab_reference(inputCsv, outputCsv)
% Independent convolution/MMSE reference. C++ outputs are not calculation inputs.
opts = detectImportOptions(inputCsv, 'Delimiter', ',');
data = readtable(inputCsv, opts);
h = [1; 0.65; 0; 0.35];
h = h / norm(h);
fid = fopen(outputCsv, 'w');
if fid < 0
    error('BLOCKED_STAGE07_MATLAB_OUTPUT', 'cannot open output');
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, 'vectorId,kind,caseId,ebn0Db,sigma2,outputLength,convolution,rhs,xHat,hardDecision,solverResidual\n');
for row = 1:height(data)
    x = parseDoubles(data.inputSymbols(row));
    kind = string(data.kind(row));
    sigma2 = numericAt(data.sigma2, row);
    ebn0Db = numericAt(data.ebn0Db, row);
    H = zeros(numel(x) + numel(h) - 1, numel(x));
    for column = 1:numel(x)
        H(column:column+numel(h)-1, column) = h;
    end
    convolution = H * x;
    rhs = [];
    xhat = [];
    hard = "";
    residual = 0;
    if kind == "MMSE"
        z = parseDoubles(data.standardGaussian(row));
        received = convolution + sqrt(sigma2) * z;
        A = H' * H + sigma2 * eye(numel(x));
        rhs = H' * received;
        xhat = A \ rhs;
        hard = join(string(double(xhat < 0)), "");
        residual = norm(A*xhat-rhs) / max(1, norm(rhs));
    end
    fprintf(fid, '%s,%s,%s,%.17g,%.17g,%d,"%s","%s","%s","%s",%.17g\n', ...
        char(string(data.vectorId(row))), char(kind), char(string(data.caseId(row))), ebn0Db, ...
        sigma2, numel(convolution), char(serialize(convolution)), char(serialize(rhs)), ...
        char(serialize(xhat)), char(hard), residual);
end
fprintf('PASS_STAGE07_MULTIPATH_VALIDATION_MATLAB rows=%d\n', height(data));
end

function value = numericAt(column, row)
if isnumeric(column)
    value = column(row);
else
    value = str2double(string(column(row)));
end
end

function values = parseDoubles(text)
parts = split(string(text), ';');
values = str2double(parts(:));
end

function text = serialize(values)
if isempty(values)
    text = "";
else
    text = join(compose('%.17g', values(:)), ';');
end
end
