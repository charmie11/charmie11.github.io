function table_to_csv(source) {
    const columns = Object.keys(source.data);
    const nrows = source.get_length();
    const lines = [columns.join(',')];

    for (let i = 0; i < nrows; i++) {
        let row = [];
        for (let j = 0; j < columns.length; j++) {
            const column = columns[j];
            let value = source.data[column][i];

            if (isNaN(value) || value === '') {
                value = '';
            } else {
                value = parseFloat(value).toFixed(15);
            }
            row.push(value);
        }
        lines.push(row.join(','));
    }
    return lines.join('\n').concat('\n');
}

const filename = 'data_result.csv';
const filetext = table_to_csv(source);
const blob = new Blob([filetext], { type: 'text/csv;charset=utf-8;' });

// Addresses IE
if (navigator.msSaveBlob) {
    navigator.msSaveBlob(blob, filename);
} else {
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.target = '_blank';
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.dispatchEvent(new MouseEvent('click'));
    document.body.removeChild(link);
}
