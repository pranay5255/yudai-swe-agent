const Mutation = require('../../mutation');

function GBOperator() {
    this.ID = "GB";
    this.name = "gas-bomb";
}

GBOperator.prototype.getMutations = function(file, source, visit) {
    const mutations = [];

    // Funzione per controllare se un nodo contiene chiamate a `call`
    function expressionContainsCall(node) {
        if (!node) return false;

        // Controlla se il nodo è una chiamata a `call`
        if (node.memberName === 'call') {
            return true;
        }

        if(node.type === 'UnaryOperation'){
            return expressionContainsCall(node.subExpression);
        }

        if (node.type === 'BinaryOperation') {
            return expressionContainsCall(node.right);
        }

        // Controlla se uno degli argomenti contiene una chiamata a `call`
        if (Array.isArray(node.arguments) && node.arguments.some(arg => expressionContainsCall(arg))) {
            return true;
        }

        // Ricorsione per controllare l'espressione principale
        return node.expression ? expressionContainsCall(node.expression) : false;
    }

    // Funzione per gestire le mutazioni
    const handleMutation = (node) => {
        const start = node.range[0];
        const end = node.range[1] + 1;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);

        // Sostituisci la sintassi `gas` se già esistente o aggiungi `.gas(10000)`
        let mutatedString = original
            // Sostituisce qualsiasi parametro `gas` esistente con `.gas(10000)`
            .replace(/\.gas\(\d+\)/g, '.gas(10000)')
            // Se non esiste `.gas(...)`, lo aggiunge dopo `call`
            .replace(/(\bcall\b)(?!\.gas\()/, '$1.gas(10000)');

        // Aggiungi la mutazione alla lista
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, mutatedString, this.ID));
    };

    visit({
        VariableDeclarationStatement: (node) => {
            if (node.initialValue && expressionContainsCall(node.initialValue.expression)) {
                handleMutation(node.initialValue.expression);
            }
        },
        IfStatement: (node) => {
            
            if (expressionContainsCall(node.condition)) {
                handleMutation(node.condition);
            }
        },
        ExpressionStatement: (node) => {
            if (expressionContainsCall(node.expression)) {
                handleMutation(node.expression);
            }
        }
    });

    return mutations;
};

module.exports = GBOperator;
