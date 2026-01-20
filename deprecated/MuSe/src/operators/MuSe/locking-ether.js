const Mutation = require('../../mutation');

function LEOperator() {
  this.ID = "LE";
  this.name = "locking-ether";
}

LEOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];
  const targetMethods = [
    "send",
    "transfer",
    "call",
    "staticcall",
    "delegatecall",
    "callcode",
    "selfdestruct"
  ];
  const operator = this;

  const candidateFunctions = new Map(); // nome -> nodo
  const calledFunctions = new Set(); // nomi delle funzioni chiamate

  visit({
    ContractDefinition: (contractNode) => {
      if (contractNode.kind !== "contract") return;

      // 1. Raccogliamo le funzioni candidate
      contractNode.subNodes.forEach((subNode) => {
        if (subNode.type === "FunctionDefinition" && subNode.name) {
          let containsTarget = false;

          const searchTargetCalls = (node) => {
            if (!node || typeof node !== 'object') return;

            if (node.type === "FunctionCall") {
              const callee = node.expression;
              if (callee?.type === "Identifier" && targetMethods.includes(callee.name)) {
                containsTarget = true;
              } else if (callee?.type === "MemberAccess" && targetMethods.includes(callee.memberName)) {
                containsTarget = true;
              }
            }

            for (const key in node) {
              const value = node[key];
              if (typeof value === 'object') {
                Array.isArray(value) ? value.forEach(searchTargetCalls) : searchTargetCalls(value);
              }
            }
          };

          searchTargetCalls(subNode.body);

          if (containsTarget) {
            candidateFunctions.set(subNode.name, subNode);
          }
        }
      });

      // 2. Trova tutte le funzioni chiamate nel contratto
      const findCalledFunctions = (node) => {
        if (!node || typeof node !== 'object') return;

        if (node.type === "FunctionCall" && node.expression?.type === "Identifier") {
          calledFunctions.add(node.expression.name);
        } else if (node.type === "FunctionCall" && node.expression?.type === "MemberAccess") {
          calledFunctions.add(node.expression.memberName);
        }

        for (const key in node) {
          const value = node[key];
          if (typeof value === 'object') {
            Array.isArray(value) ? value.forEach(findCalledFunctions) : findCalledFunctions(value);
          }
        }
      };

      findCalledFunctions(contractNode);

      // 3. Elimina solo le candidate NON chiamate
      for (const [funcName, subNode] of candidateFunctions.entries()) {
        if (!calledFunctions.has(funcName)) {
          mutations.push(new Mutation(
            file,
            subNode.range[0],
            subNode.range[1] + 1,
            subNode.loc.start.line,
            subNode.loc.end.line,
            source.slice(subNode.range[0], subNode.range[1] + 1),
            "",
            operator.ID
          ));
        }
      }
    }
  });

  return mutations;
};

module.exports = LEOperator;
