const Mutation = require('../../mutation');

function UR2Operator() {
    this.ID = "UR2";
    this.name = "unused-return-2";
}

function hasFunctionCall(node) {
    if (!node) return false;

    if (node.type === "FunctionCall") {
        return true;
    }

    if (node.type === "BinaryOperation") {
        return (
            hasFunctionCall(node.left) ||
            hasFunctionCall(node.right)
        );
    }

    if (node.type === "MemberAccess" || node.type === "IndexAccess") {
        return hasFunctionCall(node.expression);
    }

    return false;
}

function getDefaultValue(typeName) {
    if (/^uint\d*$/.test(typeName) || /^int\d*$/.test(typeName)) {
        return '0';
    }
    if (/^bytes\d+$/.test(typeName)) {
        return '0';
    }
    switch (typeName) {
        case 'bytes':
            return 'new bytes(0)';
        case 'bool':
            return 'false';
        case 'string':
            return '""';
        case 'address':
            return 'address(0)';
        default:
            return null;
    }
}

UR2Operator.prototype.getMutations = function(file, source, visit) {
    const mutations = [];

    visit({
        FunctionDefinition: (funcNode) => {
            const functionStart = funcNode.range[0];
            const functionEnd = funcNode.range[1];

            funcNode.body && visit({
                VariableDeclarationStatement: (node) => {
                    const start = node.range[0];
                    const end = node.range[1];

                    if (
                        start >= functionStart &&
                        end <= functionEnd &&
                        node.initialValue &&
                        hasFunctionCall(node.initialValue) &&
                        Array.isArray(node.variables) &&
                        node.variables.length > 0
                    ) {
                        // Salta se qualunque variabile ha tipo ArrayTypeName (ignorando buchi)
                        if (node.variables.some(v => v && v.typeName && (v.typeName.type === "ArrayTypeName" || v.typeName.type === "UserDefinedTypeName"))) {
                            return;
                        }

                        const original = source.slice(start, end);
                        const declarations = [];

                        for (const variable of node.variables) {
                            if (!variable || !variable.typeName || !variable.name) {
                                continue; // buco nella tupla: lo ignoriamo
                            }

                            if (variable.typeName.name) {
                                let type = variable.typeName.name;

                                if (variable.storageLocation) {
                                    type += ' ' + variable.storageLocation;
                                }

                                if (variable.typeName.stateMutability) {
                                    type += ' ' + variable.typeName.stateMutability;
                                }

                                const name = variable.name;
                                const defaultValue = getDefaultValue(variable.typeName.name);

                                if (defaultValue === null) {
                                    continue;
                                }

                                declarations.push(`${type} ${name} = ${defaultValue};`);
                            }
                        }

                        if (declarations.length > 0) {
                            const rhsCode = source.slice(node.initialValue.range[0], node.initialValue.range[1] + 1);
                            const mutatedString = `${declarations.join(' ')} ${rhsCode}`;
                            mutations.push(new Mutation(file, start, end, node.loc.start.line, node.loc.end.line, original, mutatedString, this.ID));
                        }
                    }
                }
            });
        }
    });

    return mutations;
};


module.exports = UR2Operator;
