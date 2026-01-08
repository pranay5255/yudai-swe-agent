const Mutation = require("../../mutation");

/**
 * The MODOperator class implements a mutation operator that targets function modifiers in the code.
 * The MODOperator specifically removes modifiers from function definitions to create different mutants
 * and test whether the existing tests can detect these changes.
 */

function MODOperator() {
  this.ID = "MOD";
  this.name = "modifier-deletion";
}

/**
 * The getMutations method generates a list of mutations for the given source code.
 * It scans the code for function definitions and creates mutations by removing function modifiers.
 *
 * @param {string} file - The name of the file being mutated.
 * @param {string} source - The source code of the file.
 * @param {function} visit - A function to visit nodes in the source code's abstract syntax tree (AST).
 * @returns {Array} - An array of Mutation objects representing the generated mutations.
 */
MODOperator.prototype.getMutations = function(file, source, visit) {
  const mutations = [];

  visit({
    FunctionDefinition: (node) => {
      let replacement;
      // Check if the function has any modifiers
      if (node.modifiers.length > 0) {
        const start = node.range[0];
        const end = node.body.range[0];
        const startLine = node.loc.start.line;
        const endLine = node.body.loc.start.line;
        const original = source.substring(start, end); // Function signature

        // Get the first modifier
        var mod = source.slice(node.modifiers[0].range[0], node.modifiers[0].range[1] + 1);

        // Create the replacement code by removing the modifier
        replacement = original.replace(mod, "");

        // Add the mutation to the list
        mutations.push(new Mutation(file, start, end, startLine, endLine, original, replacement, this.ID));
      }
    }
  });

  return mutations;
};

module.exports = MODOperator;
