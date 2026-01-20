const Mutation = require('../../mutation');

/**
 * TOROperator is a mutation testing operator designed to replace transaction origin references in the code.
 * 
 * **Purpose**:
 * The operator targets occurrences of `tx.origin` and `msg.sender` in the contract code. It replaces `tx.origin` with `msg.sender` and vice versa to test how such changes affect contract behavior and security.
 * 
 * **How It Works**:
 * 1. **Identify Usage of `tx.origin` and `msg.sender`**: The script identifies places in the code where `tx.origin` or `msg.sender` are used.
 * 2. **Perform Replacements**:
 *    - **Replace `tx.origin`**: Each occurrence of `tx.origin` is replaced with `msg.sender`.
 *    - **Replace `msg.sender`**: Each occurrence of `msg.sender` is replaced with `tx.origin`.
 * 3. **Create Mutation Instances**: It creates and records mutations reflecting these replacements.
 * 4. **Return Mutations**: The list of mutations is returned for testing and further analysis.
 */

function TOROperator() {
  this.ID = "TOR";
  this.name = "transaction-origin-replacement";
}

TOROperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    MemberAccess: (node) => {
      const start = node.range[0];
      const end = node.range[1] + 1;
      const startLine = node.loc.start.line;
      const endLine = node.loc.end.line;
      const original = source.slice(start, end);

      if (node.memberName === "origin") {
        // Replace tx.origin with msg.sender
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, "msg.sender", this.ID));
      } else if (node.memberName === "sender") {
        // Replace msg.sender with tx.origin
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, "tx.origin", this.ID));
      }
    }
  });

  return mutations;
};

module.exports = TOROperator;
