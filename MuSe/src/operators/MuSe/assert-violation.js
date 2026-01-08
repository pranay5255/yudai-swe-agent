const Mutation = require('../../mutation');

function AVOperator() {
    this.ID = "AV"; // Unique ID for the operator
    this.name = "assert-violation"; // Name of the operator
}

AVOperator.prototype.getMutations = function(file, source, visit) {
    const mutations = [];

    visit({
        FunctionCall: (node) => {
            const functionCall = node.expression;

            // Verifica se il nodo è un 'Identifier' e ha un nome
            if (functionCall.type === 'Identifier' && functionCall.name) {
                const functionName = functionCall.name;

                // Verifica se la funzione chiamata è `assert` o `require`
                if (functionName === 'assert' || functionName === 'require') {
                    const start = node.range[0];
                    const end = node.range[1];
                    const startLine = node.loc.start.line;
                    const endLine = node.loc.end.line;
                    const original = source.slice(start, end);

                    // Ottieni gli argomenti della funzione dalla proprietà 'arguments' del nodo
                    const args = source.slice(node.arguments[0].range[0], node.arguments[node.arguments.length - 1].range[1]+1);

                    // Se è `assert`, sostituiscila con `require` mantenendo gli argomenti
                    let replacement;
                    if (functionName === 'assert') {
                        replacement = `require(${args}`;
                    } else if (functionName === 'require') {
                        replacement = `assert(${args}`;
                    }

                    // Crea una mutazione e aggiungila alla lista
                    mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
                }
            }
        }
    });

    return mutations;
};

module.exports = AVOperator;
