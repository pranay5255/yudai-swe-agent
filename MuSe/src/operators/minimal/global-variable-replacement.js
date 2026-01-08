const Mutation = require("../../mutation");

/**
 * The GVROperator class implements a mutation operator that targets global variables and constants in the code.
 * The GVROperator specifically modifies global variables and constants, such as "block.timestamp" or "gasleft", 
 * to create different variants of the code and test whether the existing tests can detect these changes.
 */

function GVROperator() {
  this.ID = "GVR";
  this.name = "global-variable-replacement";
}

/**
 * The getMutations method generates a list of mutations for the given source code.
 * It scans the code for global variable accesses and function calls, creating mutations by replacing these 
 * global variables and constants with other values.
 *
 * @param {string} file - The name of the file being mutated.
 * @param {string} source - The source code of the file.
 * @param {function} visit - A function to visit nodes in the source code's abstract syntax tree (AST).
 * @returns {Array} - An array of Mutation objects representing the generated mutations.
 */
GVROperator.prototype.getMutations = function(file, source, visit) {

  const ID = this.ID;
  const mutations = [];

  // Handle member accesses of global variables
  visit({
    MemberAccess: (node) => {
      var keywords = ["timestamp", "number", "gasLimit", "difficulty", "gasprice", "value", "blockhash", "coinbase"];
      if (keywords.includes(node.memberName)) {
        const start = node.range[0];
        const end = node.range[1] + 1;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);

        // Replace 'value' with 'tx.gasprice' if accessed via 'msg'
        if (node.memberName === "value") {
          if (node.expression.name === "msg") {
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "tx.gasprice", ID));
          }
        } 
        // Replace 'difficulty', 'number', 'timestamp', and 'coinbase' based on their usage
        else if (node.expression.name === "block") {
          if (node.memberName === "difficulty") {
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "block.number", ID));
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "block.timestamp", ID));
          } else if (node.memberName === "number") {
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "block.difficulty", ID));
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "block.timestamp", ID));
          } else if (node.memberName === "timestamp") {
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "block.difficulty", ID));
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "block.number", ID));
          } else if (node.memberName === "coinbase") {
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "tx.origin", ID));
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "msg.sender", ID));
          } else if (node.memberName === "gaslimit") {
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "tx.gasprice", ID));
            mutations.push(new Mutation(file, start, end, startLine, endLine, original, "gasleft()", ID));
          }
        } 
        // Replace 'gasprice' accessed via 'tx'
        else if (node.expression.name === "tx" && node.memberName === "gasprice") {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, "gasleft()", ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, "block.gaslimit", ID));
        }
      }
    }
  });

  // Handle function calls to global functions
  visit({
    FunctionCall: (node) => {
      const start = node.range[0];
      const end = node.range[1] + 1;
      const startLine = node.loc.start.line;
      const endLine = node.loc.end.line;
      const original = source.slice(start, end);

      // Replace 'gasleft' with 'tx.gasprice' or 'block.gaslimit'
      if (node.expression.name) {
        if (node.expression.name === "gasleft") {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, "tx.gasprice", ID));
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, "block.gaslimit", ID));
        } else if (node.expression.name === "blockhash") {
          mutations.push(new Mutation(file, start, end, startLine, endLine, original, "msg.sig", ID));
        }
      }
    }
  });

  // Handle identifiers that are aliases for global variables
  visit({
    Identifier: (node) => {
      // Replace 'now' with 'block.timestamp'
      if (node.name === "now") {
        const start = node.range[0];
        const end = node.range[1] + 1;
        const startLine = node.loc.start.line;
        const endLine = node.loc.end.line;
        const original = source.slice(start, end);
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, "block.difficulty", ID));
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, "block.number", ID));
      }
    }
  });

  return mutations;
};

module.exports = GVROperator;
