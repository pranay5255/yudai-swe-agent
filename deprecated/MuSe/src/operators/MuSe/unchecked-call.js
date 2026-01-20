const Mutation = require('../../mutation');

function UCOperator() {
    this.ID = "UC";
    this.name = "unchecked-call";
}

UCOperator.prototype.getMutations = function(file, source, visit) {
    const mutations = [];

    const isCall = (node) => {
        if (!node || !node.type) return false;
        return node.type === 'MemberAccess' &&  (node.memberName === 'call' || 
            node.memberName === 'delegatecall' || node.memberName === 'staticcall' || node.memberName === 'callcode');
    }

    // Funzione per controllare se un nodo contiene chiamate a `call`
    const requireContainsCall = (node) => {
        // Funzione ricorsiva per controllare le espressioni
        const checkExpression = (expr) => {
            if (!expr || !expr.type) return false;

            if (expr.type === 'MemberAccess' &&
                ['call', 'delegatecall', 'staticcall', 'callcode'].includes(expr.memberName)) {
                const start = node.range[0];
                const end = node.range[1];
                return true;
            }

            if (node.type === 'UnaryOperation'){
                return checkExpression(node.subExpression);
            }

            if (node.type === 'BinaryOperation') {
                return checkExpression(node.right);
            }

            // Se l'espressione ha un membro, controlla ricorsivamente
            if (expr.expression) {
                return checkExpression(expr.expression);
            }

            return false;
        };

        // Controlla se il tipo di dichiarazione è ExpressionStatement
        if (node.type &&
            node.type === 'ExpressionStatement' &&
            node.expression &&
            node.expression.type &&
            node.expression.type === 'FunctionCall' &&
            (node.expression.expression.name === 'require' || node.expression.expression.name === 'assert')
        ) {
            return node.expression.arguments.some(arg => {
                if( arg.type === "UnaryOperation"){
                    return checkExpression(arg.subExpression);
                }
                return checkExpression(arg);
            });
        }
        return false;
    };


    visit({
        ExpressionStatement: (node) => {
            if (requireContainsCall(node)) {
                const start = node.range[0];
                const end = node.range[1];
                const startLine = node.loc.start.line;
                const endLine = node.loc.end.line;
                const original = source.slice(start, end);

                let mutatedString = original
                    .replace(/^require\s*\(\s*!?\s*/, '')
                    .replace(/^assert\s*\(\s*!?\s*/, '')
                    .replace(/\s*\)\s*;?$/, '');

                // Rimuove tutto dalla virgola successiva all'ultimo ")" fino a ";" finale
                const lastClosingParenIndex = mutatedString.lastIndexOf(')');
                const commaIndex = mutatedString.indexOf(',', lastClosingParenIndex);
                if (commaIndex !== -1) {
                    mutatedString = mutatedString.slice(0, commaIndex).trim();
                }

                mutations.push(new Mutation(file, start, end, startLine, endLine, original, mutatedString, this.ID));
            }
        },
        IfStatement: (node) => {
            const condition = node.condition;
            if ((condition.expression && isCall(condition.expression)) ||
                (condition.subExpression && condition.subExpression.expression && isCall(condition.subExpression.expression))) {

                const start = node.range[0];
                const end = node.range[1] + 1;
                const original = source.slice(start, end);
                const callExpression = condition.expression
                    ? source.slice(condition.range[0], condition.range[1] + 1)
                    : source.slice(condition.subExpression.range[0], condition.subExpression.range[1] + 1);
                const cleaned = original.replace(/\bthrow\s*;\s*/g, '')
                                        .replace(/\brevert\s*;\s*/g, '')
                                        .trim();
                let trueBranch = "";

                if (cleaned.includes("{")) {
                    const startBrace = cleaned.indexOf("{");
                    let count = 0, endBrace = -1;
                    for (let i = startBrace; i < cleaned.length; i++) {
                        if (cleaned[i] === "{") count++;
                        else if (cleaned[i] === "}") {
                            count--;
                            if (count === 0) { endBrace = i; break; }
                        }
                    }
                    trueBranch = cleaned.slice(startBrace + 1, endBrace).trim();
                } else {
                    trueBranch = cleaned.slice(cleaned.indexOf(")") + 2)
                                          .split("else")[0].trim();
                }
                const mutatedString = `${callExpression}; ${trueBranch}`;

                mutations.push(new Mutation(file, start, end, node.loc.start.line, node.loc.end.line, original, mutatedString, this.ID));
            }
        }
    });

    return mutations;
};

module.exports = UCOperator;
