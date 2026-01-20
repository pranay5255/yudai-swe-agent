const Mutation = require('../../mutation');

function USDOperator() {
  this.ID = "USD";
  this.name = "unprotected-selfdestruct";
}

USDOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    ContractDefinition: (contractNode) => {
      if (contractNode.kind === "interface") {
        return; // Evita di applicare mutazioni nelle interfacce
      }
    },
    FunctionDefinition: (node) => {
      // Ignora i costruttori
      if (node.isConstructor) {
        return;
      }

      let containsSelfDestruct = false;

      if (node.body && node.body.type === "Block" && Array.isArray(node.body.statements)) {
        for (const statement of node.body.statements) {
          if (statement.type === "ExpressionStatement" && statement.expression && statement.expression.type === "FunctionCall") {
            const callee = statement.expression.expression;
            if (callee && ((callee.type === "Identifier" && callee.name === "selfdestruct") ||
                           (callee.type === "MemberAccess" && callee.memberName === "selfdestruct"))) {
              containsSelfDestruct = true;
              break;
            }
          }
        }
      }

      if (containsSelfDestruct) {
        let mutatedSource = source.slice(node.range[0], node.range[1] + 1);

        // Modifica la visibilità della funzione
        mutatedSource = mutatedSource.replace(/\b(private|external|internal)\b/g, "public");

        // Rimuove tutti i modifier dalla dichiarazione della funzione
        if (node.modifiers && node.modifiers.length > 0) {
          node.modifiers.forEach(modifier => {
            const modifierRegex = new RegExp(`\\b${modifier.name}\\b`, "g");
            mutatedSource = mutatedSource.replace(modifierRegex, "");
          });
        }

        mutations.push(new Mutation(
          file,
          node.range[0],
          node.range[1] + 1,
          node.loc.start.line,
          node.loc.end.line,
          source.slice(node.range[0], node.range[1] + 1),
          mutatedSource,
          this.ID
        ));
      }
    }
  });

  return mutations;
};

module.exports = USDOperator;
