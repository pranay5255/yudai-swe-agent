const Mutation = require('../../mutation');

function CLOperator() {
    this.ID = "CL";
    this.name = "calls-loop";
}

CLOperator.prototype.getMutations = function(file, source, visit) {
    const mutations = [];

    // Funzione per controllare se un nodo contiene chiamate a `send`, `call` o `transfer`
    function expressionContainsSendCallTransfer(node) {
        if (!node) return false;
        
        // Controlla se il nodo è una chiamata a `call`
        if (node.memberName === 'call' || node.memberName === 'transfer' || node.memberName === 'send') {
            return true;
        }
        
        // Controlla se uno degli argomenti contiene una chiamata a `call`
        const hasSendCallTransferInArgs = Array.isArray(node.arguments) && node.arguments.some(arg => expressionContainsSendCallTransfer(arg));
        
        // Ricorsione per controllare l'espressione principale
        const hasSendCallTransferInExpression = node.expression ? expressionContainsSendCallTransfer(node.expression) : false;

        // Ritorna true se uno dei due è true
        return hasSendCallTransferInArgs || hasSendCallTransferInExpression;
    }
    
    const handleMutation = (node) => {
        const start = node.range[0];
        const end = node.range[1] + 2;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);

        //console.log(JSON.stringify(node));

        const mutationCode = `for (uint iCL = 0; iCL < 1000; iCL++) { ${original} }`;
        
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, mutationCode, this.ID));
    }


    visit({

        ExpressionStatement: (node) => {
            if (expressionContainsSendCallTransfer(node.expression)) {
                handleMutation(node.expression);
            }
        },

        IfStatement: (node) => {
            if (expressionContainsSendCallTransfer(node.condition)) {
                handleMutation(node);
            }
            if (expressionContainsSendCallTransfer(node.condition.subExpression)) {
                handleMutation(node);
            }
        }
    });

    return mutations;
};
module.exports = CLOperator;
