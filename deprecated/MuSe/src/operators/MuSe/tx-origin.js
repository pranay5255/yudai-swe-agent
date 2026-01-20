const Mutation = require('../../mutation');

/**
 * TXOperator is a mutation testing operator designed to replace transaction origin references in the code.
 * 
 * **Purpose**:
 * The operator targets occurrences of `msg.sender` in the contract code. It replaces `msg.sender` with `tx.origin` and vice versa to test how such changes affect contract behavior and security.
 * 
 * **How It Works**:
 * 1. **Identify Usage of`msg.sender`**: The script identifies places in the code where `tx.origin` or `msg.sender` are used.
 * 2. **Perform Replacements**:
 *    - **Replace `msg.sender`**: Each occurrence of `msg.sender` is replaced with `tx.origin`.
 * 3. **Create Mutation Instances**: It creates and records mutations reflecting these replacements.
 * 4. **Return Mutations**: The list of mutations is returned for testing and further analysis.
 */

function TXOperator() {
  this.ID = "TX";
  this.name = "tx-origin";
}

TXOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    BinaryOperation: (node) => {
          // Verifica che l'operatore sia "=="
      if (node.operator === "==" ||
        node.operator === "!=") {
        // Verifica che il lato sinistro sia un Identifier
        const leftIsIdentifier = node.left.type === "Identifier";
        const rightIsIdentifier = node.right.type === "Identifier";

        // Verifica che il lato destro o sinistro sia un MemberAccess con memberName uguale a "sender"
        const rightIsValidMemberAccess =
          node.right.type === "MemberAccess" &&
          node.right.memberName === "sender";
        const leftIsValidMemberAccess =
          node.left.type === "MemberAccess" &&
          node.left.memberName === "sender";

        // Stampa o ritorna il risultato della verifica
        if (leftIsIdentifier && rightIsValidMemberAccess) {
          const start = node.right.range[0];
          const end = node.right.range[1] + 1;
          const startLine = node.right.loc.start.line;
          const endLine = node.right.loc.end.line;
          const original = source.slice(start, end);

          // Crea la mutazione sostituendo "msg.sender" con "tx.origin"
          mutations.push(
            new Mutation(file, start, end, startLine, endLine, original, "tx.origin", this.ID)
          );

        } 

        if (rightIsIdentifier && leftIsValidMemberAccess) {
          const start = node.left.range[0];
          const end = node.left.range[1] + 1;
          const startLine = node.left.loc.start.line;
          const endLine = node.left.loc.end.line;
          const original = source.slice(start, end);

          // Crea la mutazione sostituendo "msg.sender" con "tx.origin"
          mutations.push(
            new Mutation(file, start, end, startLine, endLine, original, "tx.origin", this.ID)
          );

        } 
      } 
    }
  });

  return mutations;
};

module.exports = TXOperator;