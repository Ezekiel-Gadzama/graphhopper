/*
 *  Licensed to GraphHopper GmbH under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for
 *  additional information regarding copyright ownership.
 *
 *  GraphHopper GmbH licenses this file to you under the Apache License,
 *  Version 2.0 (the "License"); you may not use this file except in
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
package com.graphhopper.routing.weighting.custom;

import com.graphhopper.routing.ev.EncodedValueLookup;
import com.graphhopper.routing.ev.RoadClass;
import com.graphhopper.util.Helper;
import org.codehaus.janino.Scanner;
import org.codehaus.janino.*;
import com.graphhopper.json.*;
import java.io.StringReader;
import java.util.*;

import static com.graphhopper.routing.weighting.custom.CustomModelParser.IN_AREA_PREFIX;

/**
 * Expression visitor for the if or else_if condition.
 */
class ConditionalExpressionVisitor implements Visitor.AtomVisitor<Boolean, Exception> {

    private static final Set<String> allowedMethodParents = new HashSet<>(Arrays.asList("edge", "Math", "country"));
    private static final Set<String> allowedMethods = new HashSet<>(Arrays.asList("ordinal", "getDistance", "getName",
            "contains", "sqrt", "abs", "isRightHandTraffic"));
    private final ParseResult result;
    private final TreeMap<Integer, Replacement> replacements = new TreeMap<>();
    private final NameValidator variableValidator;
    private final ClassHelper classHelper;
    private String invalidMessage;

    public ConditionalExpressionVisitor(ParseResult result, NameValidator variableValidator, ClassHelper classHelper) {
        this.result = result;
        this.variableValidator = variableValidator;
        this.classHelper = classHelper;
    }

    // allow only methods and other identifiers (constants and encoded values)
    boolean isValidIdentifier(String identifier) {
        // First check if it's a valid variable name
        if (variableValidator.isValid(identifier)) {
            if (!Character.isUpperCase(identifier.charAt(0)))
                result.guessedVariables.add(identifier);
            return true;
        }
        // If not a variable, it might be an enum constant - defer validation to binary operation handling
        return true;
    }
    @Override
    public Boolean visitRvalue(Java.Rvalue rv) throws Exception {
        if (rv instanceof Java.AmbiguousName) {
            Java.AmbiguousName n = (Java.AmbiguousName) rv;
            if (n.identifiers.length == 1) {
                String arg = n.identifiers[0];

                // Handle area checks first
                if (arg.startsWith(IN_AREA_PREFIX)) {
                    int start = rv.getLocation().getColumnNumber() - 1;
                    replacements.put(start, new Replacement(start, arg.length(),
                            CustomWeightingHelper.class.getSimpleName() + ".in(this." + arg + ", edge)"));
                    result.guessedVariables.add(arg);
                    return true;
                }

                // Check if this is a variable reference
                if (variableValidator.isValid(arg)) {
                    if (!Character.isUpperCase(arg.charAt(0))) {
                        result.guessedVariables.add(arg);
                    }
                    return true;
                }

                // If not a valid variable, it might be an enum constant in a comparison
                // We'll handle this in the binary operation case
                invalidMessage = "'" + arg + "' not available";
                return false;
            }
            invalidMessage = "identifier " + n + " invalid";
            return false;
        }
        if (rv instanceof Java.Literal) {
            return true;
        } else if (rv instanceof Java.UnaryOperation) {
            Java.UnaryOperation uo = (Java.UnaryOperation) rv;
            if (uo.operator.equals("!")) return uo.operand.accept(this);
            if (uo.operator.equals("-")) return uo.operand.accept(this);
            return false;
        } else if (rv instanceof Java.MethodInvocation) {
            Java.MethodInvocation mi = (Java.MethodInvocation) rv;
            if (allowedMethods.contains(mi.methodName) && mi.target != null) {
                Java.AmbiguousName n = (Java.AmbiguousName) mi.target.toRvalue();
                if (n.identifiers.length == 2) {
                    if (allowedMethodParents.contains(n.identifiers[0])) {
                        // edge.getDistance(), Math.sqrt(x) => check target name i.e. edge or Math
                        if (mi.arguments.length == 0) {
                            result.guessedVariables.add(n.identifiers[0]); // return "edge"
                            return true;
                        } else if (mi.arguments.length == 1) {
                            // return "x" but verify before
                            return mi.arguments[0].accept(this);
                        }
                    } else if (variableValidator.isValid(n.identifiers[0])) {
                        // road_class.ordinal()
                        if (mi.arguments.length == 0) {
                            result.guessedVariables.add(n.identifiers[0]); // return road_class
                            return true;
                        }
                    }
                }
            }
            invalidMessage = mi.methodName + " is an illegal method in a conditional expression";
            return false;
        } else if (rv instanceof Java.ParenthesizedExpression) {
            return ((Java.ParenthesizedExpression) rv).value.accept(this);
        } else if (rv instanceof Java.BinaryOperation) {
            Java.BinaryOperation binOp = (Java.BinaryOperation) rv;
            if (binOp.lhs instanceof Java.AmbiguousName && ((Java.AmbiguousName) binOp.lhs).identifiers.length == 1) {
                String lhVarAsString = ((Java.AmbiguousName) binOp.lhs).identifiers[0];

                if (binOp.rhs instanceof Java.AmbiguousName && ((Java.AmbiguousName) binOp.rhs).identifiers.length == 1) {
                    String rhValueAsString = ((Java.AmbiguousName) binOp.rhs).identifiers[0];

                    if (variableValidator.isValid(lhVarAsString)) {
                        String enumType = classHelper.getClassName(lhVarAsString);
                        if (enumType != null) {
                            // Create replacement with correct enum constant
                            int startRH = binOp.rhs.getLocation().getColumnNumber() - 1;
                            replacements.put(startRH, new Replacement(
                                    startRH,
                                    rhValueAsString.length(),
                                    enumType + "." + rhValueAsString.toUpperCase()
                            ));
                            result.guessedVariables.add(lhVarAsString);
                            return true;
                        }
                    }
                }
            }
            return binOp.lhs.accept(this) && binOp.rhs.accept(this);
        }
        return false;
    }

    @Override
    public Boolean visitPackage(Java.Package p) {
        return false;
    }

    @Override
    public Boolean visitType(Java.Type t) {
        return false;
    }

    @Override
    public Boolean visitConstructorInvocation(Java.ConstructorInvocation ci) {
        return false;
    }

    /**
     * Enforce simple expressions of user input to increase security.
     *
     * @return ParseResult with ok if it is a valid and "simple" expression. It contains all guessed variables and a
     * converted expression that includes class names for constants to avoid conflicts e.g. when doing "toll == Toll.NO"
     * instead of "toll == NO".
     */
    static ParseResult parse(String expression, NameValidator validator, ClassHelper helper) {
        System.out.println("\nStarting parse for expression: " + expression);
        ParseResult result = new ParseResult();

        try {
            System.out.println("Creating parser and scanner...");
            Parser parser = new Parser(new Scanner("ignore", new StringReader(expression)));

            System.out.println("Parsing conditional expression...");
            Java.Atom atom = parser.parseConditionalExpression();
            System.out.println("Parsed atom: " + atom);

            System.out.println("Checking for end of input...");
            if (parser.peek().type == TokenType.END_OF_INPUT) {
                System.out.println("End of input reached successfully");
                result.guessedVariables = new LinkedHashSet<>();

                System.out.println("Creating visitor with validator: " + validator);
                ConditionalExpressionVisitor visitor = new ConditionalExpressionVisitor(result, validator, helper);
                System.out.println("Print visitor: " + visitor);
                System.out.println("Visiting atom...");
                result.ok = atom.accept(visitor);
                result.invalidMessage = visitor.invalidMessage;

                System.out.println("Visitor result - ok: " + result.ok +
                        ", invalidMessage: " + result.invalidMessage);

                if (result.ok) {
                    System.out.println("Building converted expression...");
                    result.converted = new StringBuilder(expression.length());
                    int start = 0;
                    for (Replacement replace : visitor.replacements.values()) {
                        result.converted.append(expression, start, replace.start)
                                .append(replace.newString);
                        start = replace.start + replace.oldLength;
                    }
                    result.converted.append(expression.substring(start));
                    System.out.println("Converted expression: " + result.converted);
                }
            } else {
                System.out.println("Unexpected token after expression: " + parser.peek());
                result.invalidMessage = "Unexpected token after expression";
            }
        } catch (Exception ex) {
            System.out.println("Exception during parsing: " + ex);
            ex.printStackTrace();
            result.invalidMessage = ex.getMessage();
        }

        System.out.println("Final parse result: " + result);
        return result;
    }

    public static Set<String> findVariables(String expression, EncodedValueLookup lookup, ClassHelper classHelper) {
        NameValidator nameValidator = lookup::hasEncodedValue;
        ParseResult result = parse(expression, nameValidator, classHelper);
        return result.guessedVariables;
    }
    public static String toJavaExpression(String expression, EncodedValueLookup lookup, ClassHelper classHelper) {
        ParseResult result = parse(expression, lookup::hasEncodedValue, classHelper);
        if (!result.ok) {
            throw new IllegalArgumentException(result.invalidMessage != null ? result.invalidMessage : "Invalid expression");
        }
        return result.converted != null ? result.converted.toString() : expression;
    }

    static class Replacement {
        int start;
        int oldLength;
        String newString;

        public Replacement(int start, int oldLength, String newString) {
            this.start = start;
            this.oldLength = oldLength;
            this.newString = newString;
        }
    }

    static class ParseResult {
        boolean ok;
        String invalidMessage;
        Set<String> guessedVariables;
        StringBuilder converted;

        @Override
        public String toString() {
            return "ParseResult{" +
                    "ok=" + ok +
                    ", invalidMessage='" + invalidMessage + '\'' +
                    ", guessedVariables=" + guessedVariables +
                    ", converted=" + (converted != null ? converted.toString() : "null") +
                    '}';
        }
    }
}
