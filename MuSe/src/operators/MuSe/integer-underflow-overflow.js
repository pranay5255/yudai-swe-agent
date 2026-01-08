const Mutation = require('../../mutation');

function IUOOperator() {
    this.ID = "IUO";
    this.name = "integer-underflow-overflow";
}

function isVersionLessThan(current, target) {
    const c = current.split('.').map(Number);
    const t = target.split('.').map(Number);
    for (let i = 0; i < 3; i++) {
        if ((c[i] || 0) < (t[i] || 0)) return true;
        if ((c[i] || 0) > (t[i] || 0)) return false;
    }
    return false;
}

function isContractVersionEligible(source) {
    const match = source.match(/pragma solidity\s+([^;]+);/);
    if (match) {
        const version = (match[1].match(/(\d+\.\d+\.\d+)/) || [])[1];
        if (version) return isVersionLessThan(version, "0.8.18");
    }
    return false;
}

function stripComments(source) {
    return source
        .replace(/\/\/.*$/gm, '')
        .replace(/\/\*[\s\S]*?\*\//g, '');
}

function extractText(node, source) {
    if (!node) return "<?>";

    switch (node.type) {
        case 'Identifier':
            return node.name;
        case 'Literal':
            return String(node.value);
        case 'NumberLiteral':
            return node.number;
        case 'IndexAccess':
            return `${extractText(node.base, source)}[${extractText(node.index, source)}]`;
        case 'MemberAccess':
            return `${extractText(node.expression, source)}.${node.memberName}`;
        case 'BinaryOperation':
            return `(${extractText(node.left, source)} ${node.operator} ${extractText(node.right, source)})`;
        case 'FunctionCall':
            const args = (node.arguments || []).map(arg => extractText(arg, source)).join(", ");
            return `${extractText(node.expression, source)}(${args})`;
        default:
            if (node.range && node.range[0] !== node.range[1]) {
                return source.slice(node.range[0], node.range[1] + 1);
            }
            return "<?>";
    }
}

IUOOperator.prototype.getMutations = function (file, source, visit) {
    const mutations = [];
    const isOldVersion = isContractVersionEligible(source);
    const cleanSource = stripComments(source);
    const hasSafeMath = cleanSource.includes("SafeMath");

    const safeMathMethods = {
        add: '+',
        sub: '-',
        mul: '*',
        div: '/',
        mod: '%',
    };

    function isSafeMathCall(node) {
        return node &&
            node.type === 'FunctionCall' &&
            node.expression &&
            node.expression.type === 'MemberAccess' &&
            safeMathMethods.hasOwnProperty(node.expression.memberName) &&
            extractText(node.expression.expression, source) !== "SafeMath";
    }

    function transformSafeMath(node) {
        if (isSafeMathCall(node)) {
            const operator = safeMathMethods[node.expression.memberName];
            const args = node.arguments;
            if (!args || args.length < 1) return extractText(node, source);

            const left = node.expression.expression;
            const right = args[0];

            const leftStr = transformSafeMath(left);
            const rightStr = transformSafeMath(right);

            return `(${leftStr} ${operator} ${rightStr})`;
        }

        if (node.type === 'BinaryOperation') {
            return `${transformSafeMath(node.left)} ${node.operator} ${transformSafeMath(node.right)}`;
        }

        return extractText(node, source);
    }

    function containsSafeMath(node) {
        if (!node) return false;
        if (isSafeMathCall(node)) return true;
        if (Array.isArray(node.arguments) && node.arguments.some(containsSafeMath)) return true;
        if (node.left && containsSafeMath(node.left)) return true;
        if (node.right && containsSafeMath(node.right)) return true;
        if (node.expression && containsSafeMath(node.expression)) return true;
        return false;
    }

    if (isOldVersion) {
        if (!hasSafeMath) return [];

        const variableDeclarations = [];

        visit({
            VariableDeclaration: (node) => {
                if (node.name && node.typeName) {
                    variableDeclarations.push({
                        name: node.name,
                        type: extractText(node.typeName, source),
                        line: node.loc.start.line
                    });
                }
            }
        });

        function findClosestTypeBeforeLine(varName, currentLine) {
            let closestDecl = null;
            for (const decl of variableDeclarations) {
                if (decl.name === varName && decl.line < currentLine) {
                    if (!closestDecl || decl.line > closestDecl.line) {
                        closestDecl = decl;
                    }
                }
            }
            return closestDecl ? closestDecl.type : null;
        }

        function isIntegerType(typeName) {
            return /^u?int(\d+)?$/.test(typeName.trim());
        }

        function mutateSafeMathExpression(node, type) {
            if (!node || !node.range || !node.loc) return;

            let expression = null;

            if (type === 'ReturnStatement') expression = node.expression;
            else if (type === 'ExpressionStatement') expression = node.expression;
            else if (type === 'VariableDeclarationStatement') expression = node.initialValue;

            if (!expression || !containsSafeMath(expression)) return;

            if (
                expression.type === 'FunctionCall' &&
                expression.expression &&
                (
                    expression.expression.name === 'require' ||
                    expression.expression.name === 'assert'
                )
            ) return;

            const currentLine = node.loc.start.line;
            const identifiers = [];

            if (expression.arguments) {
                expression.arguments.forEach(arg => {
                    if (arg.type === 'Identifier') {
                        identifiers.push({ name: arg.name, line: currentLine });
                    }
                });
            }

            const allTypesOk = identifiers.every(({ name, line }) => isIntegerType(findClosestTypeBeforeLine(name, line) || ""));
            if (!allTypesOk) return;

            const original = source.slice(node.range[0], node.range[1]);
            const mutatedInner = transformSafeMath(expression);

            let mutated;
            switch (type) {
                case 'ReturnStatement':
                    mutated = `return ${mutatedInner}`;
                    break;
                case 'ExpressionStatement':
                    mutated = `${mutatedInner}`;
                    break;
                case 'VariableDeclarationStatement':
                    if (node.variables && node.variables.length > 0) {
                        const decl = node.variables[0];
                        const name = decl.name;
                        const typeName = extractText(decl.typeName, source);
                        mutated = `${typeName} ${name} = ${mutatedInner}`;
                    } else return;
                    break;
                default:
                    return;
            }

            if (original.trim() !== mutated.trim()) {
                mutations.push(new Mutation(
                    file,
                    node.range[0],
                    node.range[1],
                    node.loc.start.line,
                    node.loc.end.line,
                    original,
                    mutated,
                    "IUO1"
                ));
            }
        }

        visit({
            ExpressionStatement: function (node) {
                mutateSafeMathExpression(node, 'ExpressionStatement');
            },
            ReturnStatement: function (node) {
                mutateSafeMathExpression(node, 'ReturnStatement');
            },
            VariableDeclarationStatement: function (node) {
                mutateSafeMathExpression(node, 'VariableDeclarationStatement');
            }
        });
    }

    if (!isOldVersion) {
        const isArithmeticOp = (op) =>
            ["+", "-", "*", "/", "%", "+=", "-=", "*=", "/=", "%="].includes(op);

        function wrapInUnchecked(text) {
            const body = text.trim().replace(/;+\s*$/, '');
            return `unchecked { ${body}; }`;
        }

        function nodeContainsArithmetic(node) {
            if (!node || typeof node !== 'object') return false;

            if (
                (node.type === "Assignment" && isArithmeticOp(node.operator)) ||
                (node.type === "BinaryOperation" && isArithmeticOp(node.operator))
            ) return true;

            const fields = ['left', 'right', 'expression', 'initialValue', 'body'];

            for (const field of fields) {
                if (
                    node[field] &&
                    nodeContainsArithmetic(node[field])
                ) return true;
            }

            if (
                node.type === 'FunctionCall' &&
                Array.isArray(node.arguments) &&
                node.arguments.some(arg => nodeContainsArithmetic(arg))
            ) return true;

            return false;
        }

        visit({
            ExpressionStatement: (node) => {
                if (!node || !node.expression || !node.range || !node.loc) return;

                const expr = node.expression;

                if (
                    expr &&
                    expr.type === 'FunctionCall' &&
                    expr.expression &&
                    (expr.expression.name === 'require' || expr.expression.name === 'assert')
                ) return;

                if (!nodeContainsArithmetic(expr)) return;

                const fullText = source.slice(node.range[0], node.range[1] + 1);
                const cleaned = wrapInUnchecked(fullText);

                mutations.push(new Mutation(
                    file,
                    node.range[0],
                    node.range[1] + 1,
                    node.loc.start.line,
                    node.loc.end.line,
                    fullText,
                    cleaned,
                    "IUO2"
                ));
            }
        });
    }

    return mutations;
};

module.exports = IUOOperator;
