const Mutation = require('../../mutation');

function UROperator() {
    this.ID = "UR";
    this.name = "unused-return";
}

UROperator.prototype.getMutations = function(file, source, visit) {
    const mutations = [];
    var ranges = []; // To keep track of visited node ranges

    function hasFunctionCall(node) {
        // is FunctionCall ?
        if (node.type && node.type === "FunctionCall") {
            return true;
        }
    
        // is BinaryOperation ?, check left and right
        if (node.type && node.type === "BinaryOperation") {
            return (
                (node.left && hasFunctionCall(node.left)) || 
                (node.right && hasFunctionCall(node.right))
            );
        }
    
        // FunctionCall not found
        return false;
    }

    visit({
        FunctionDefinition: (functionNode) => {
            const functionStart = functionNode.range[0];
            const functionEnd = functionNode.range[1] + 1;

            // Estrai il codice originale della funzione
            const originalFunctionCode = source.slice(functionStart, functionEnd);
            let modifiedFunctionCode = originalFunctionCode;
            let hasMutations = false;

            visit({
                BinaryOperation: (node) => {
                    // if (!ranges.includes(node.range)) {
                    //     ranges.push(node.range);
                        const start = node.range[0];
                        const end = node.range[1] + 1;

                        if (start >= functionStart && end <= functionEnd && node.operator === '=' &&
                            (node.right.type === 'FunctionCall' || node.right.type === 'MemberAccess') &&
                            node.right.memberName !== 'sender'
                        ) {
                            // Rimuovi l'assegnazione dall'originale
                            const original = source.slice(start, end);
                            const mutatedString = original.replace(/^[^=]+=\s*/, "");

                            // Aggiorna il codice della funzione con la modifica
                            modifiedFunctionCode = modifiedFunctionCode.replace(original, mutatedString);
                            hasMutations = true;
                        }
                    //}
                },

                VariableDeclarationStatement:(node) => {
                    // if (!ranges.includes(node.range)) {
                    //     ranges.push(node.range);
                        const start = node.range[0];
                        const end = node.range[1] + 1;
  
                        if (start >= functionStart && end <= functionEnd 
                            && node.initialValue &&
                            (hasFunctionCall(node.initialValue))
                            && node.variables[0] && node.variables[0].typeName && node.variables[0].typeName.name
                            // && (node.variables[0].typeName.name === 'uint256' || node.variables[0].typeName.name === 'uint')
                        ) {
                            const original = source.slice(start, end);
                            // Identifica il contenuto della funzione chiamata (senza ridefinire la variabile)
                            const declarationMatch = original.match(/(uint(?:256)?\s+\w+\s*=\s*)([^;]+);/);
                            if (declarationMatch) {
                                const variableDeclaration = declarationMatch[1].slice(0, -3); // Parte iniziale fino al "="
                                const functionCall = declarationMatch[2];       // Parte dopo il "=" fino al ";"

                                // Mutazione: assegna 0 alla variabile e lascia la chiamata a parte
                                const mutatedString = `${variableDeclaration}; ${functionCall};`;

                                // Aggiorna il codice della funzione con la modifica
                                modifiedFunctionCode = modifiedFunctionCode.replace(original, mutatedString);
                                hasMutations = true;
                            }
                        }
                    //}
                }
            });

            // Se sono state fatte modifiche, crea una mutazione per l'intera funzione
            if (hasMutations) {
                const startLine = functionNode.loc.start.line;
                const endLine = functionNode.loc.end.line;

                mutations.push(
                    new Mutation(file, functionStart, functionEnd, startLine, endLine, originalFunctionCode, modifiedFunctionCode, this.ID)
                );
            }
        }
    });

    return mutations;
};

module.exports = UROperator;
