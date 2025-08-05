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
import com.graphhopper.json.Statement;
import com.graphhopper.routing.ev.*;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.weighting.TurnCostProvider;
import com.graphhopper.util.*;
import com.graphhopper.util.shapes.BBox;
import com.graphhopper.util.shapes.Polygon;
import com.graphhopper.util.CustomModel;
import freemarker.template.*;
import javax.tools.*;
import java.nio.file.*;
import org.locationtech.jts.geom.Polygonal;
import org.locationtech.jts.geom.prep.PreparedPolygon;
import org.slf4j.LoggerFactory;
import java.util.function.Function;

import java.io.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;

import static com.graphhopper.json.Statement.Keyword.IF;

public class CustomModelParser {
    private static final AtomicLong longVal = new AtomicLong(1);
    static final String IN_AREA_PREFIX = "in_";
    static final String BACKWARD_PREFIX = "backward_";
    public static final String OSM_ID_KEY = "osm_id";

    // Without a cache the class creation takes 10-40ms which makes routingLM8 requests 20% slower on average.
    // CH requests and preparation is unaffected as cached weighting from preparation is used.
    // Use accessOrder==true to remove oldest accessed entry, not oldest inserted.
    private static final int CACHE_SIZE = Integer.getInteger("graphhopper.custom_weighting.cache_size", 1000);
    private static final Map<String, Class<?>> CACHE = Collections.synchronizedMap(
            new LinkedHashMap<>(CACHE_SIZE, 0.75f, true) {
                protected boolean removeEldestEntry(Map.Entry eldest) {
                    return size() > CACHE_SIZE;
                }
            });

    // This internal cache ensures that the "internal" Weighting classes specified in the profiles, are never removed regardless
    // of how frequent other Weightings are created and accessed. We only need to synchronize the get and put methods alone.
    // E.g. we do not care for the race condition where two identical classes are requested and one of them is overwritten.
    // TODO perf compare with ConcurrentHashMap, but I guess, if there is a difference at all, it is not big for small maps
    private static final Map<String, Class<?>> INTERNAL_CACHE = Collections.synchronizedMap(new HashMap<>());


    private CustomModelParser() {
        // utility class
    }

    public static void parseExpressions(
            StringBuilder sb,
            EncodedValueLookup lookup, // Changed from NameValidator
            String errorContext,
            Set<String> blockedVariables,
            List<Statement> statements,
            Function<String, String> variableTransformer,
            String indentation
    ) {
        if (statements == null || statements.isEmpty())
            return;

        for (Statement stmt : statements) {
            if (stmt.isBlock()) {
                parseExpressions(sb, lookup, errorContext, blockedVariables,
                        stmt.doBlock(), variableTransformer, indentation + "    ");
            } else {
                ClassHelper classHelper = new DefaultClassHelper(lookup);
                String condition = ConditionalExpressionVisitor.toJavaExpression(stmt.condition(), lookup, classHelper);
                String value = ValueExpressionVisitor.toJavaExpression(stmt.value(), lookup);
                sb.append(indentation).append("if (").append(condition).append(") {\n");
                sb.append(indentation).append("    return ").append(value).append(";\n");
                sb.append(indentation).append("}\n");
            }
        }
    }

    private static Class<?> getCachedClass(String key, boolean isInternal) {
        if (isInternal) {
            return INTERNAL_CACHE.get(key);
        }
        return CACHE_SIZE > 0 ? CACHE.get(key) : null;
    }

    private static void cacheClass(String key, Class<?> clazz, boolean isInternal) {
        if (isInternal) {
            INTERNAL_CACHE.put(key, clazz);
            if (INTERNAL_CACHE.size() > 100) {
                CACHE.putAll(INTERNAL_CACHE);
                INTERNAL_CACHE.clear();
                LoggerFactory.getLogger(CustomModelParser.class).warn("Internal cache too large, cleared");
            }
        } else if (CACHE_SIZE > 0) {
            CACHE.put(key, clazz);
        }
    }

    private static CustomWeighting.Parameters instantiateWeighting(Class<?> clazz, CustomModel customModel, EncodedValueLookup lookup) {
        try {
            CustomWeightingHelper helper = (CustomWeightingHelper) clazz.getDeclaredConstructor().newInstance();
            helper.init(customModel, lookup, CustomModel.getAreasAsMap(customModel.getAreas()));
            return new CustomWeighting.Parameters(
                    helper::getSpeed, helper::calcMaxSpeed,
                    helper::getPriority, helper::calcMaxPriority,
                    customModel.getDistanceInfluence() == null ? 0 : customModel.getDistanceInfluence(),
                    customModel.getHeadingPenalty() == null ? Parameters.Routing.DEFAULT_HEADING_PENALTY : customModel.getHeadingPenalty());
        } catch (Exception ex) {
            throw new IllegalArgumentException("Cannot instantiate weighting", ex);
        }
    }


    public static CustomWeighting createWeighting(EncodedValueLookup lookup, TurnCostProvider turnCostProvider, CustomModel customModel) {
        if (customModel == null)
            throw new IllegalStateException("CustomModel cannot be null");
        System.out.println("na fuck up customModel: " + customModel + "  lookup: " + lookup);
        CustomWeighting.Parameters parameters = createWeightingParameters(customModel, lookup);
        return new CustomWeighting(turnCostProvider, parameters);
    }

    public static CustomWeighting2 createWeighting2(EncodedValueLookup lookup, TurnCostProvider turnCostProvider, CustomModel customModel) {
        if (customModel == null)
            throw new IllegalStateException("CustomModel cannot be null");
        CustomWeighting.Parameters parameters = createWeightingParameters(customModel, lookup);
        return new CustomWeighting2(turnCostProvider, parameters);
    }

    public static CustomWeighting.Parameters createWeightingParameters(CustomModel customModel, EncodedValueLookup lookup) {
        String key = customModel.toString();
        Class<?> clazz = getCachedClass(key, customModel.isInternal());
        if (clazz == null) {
            clazz = createClazz(customModel, lookup);
            cacheClass(key, clazz, customModel.isInternal());
        }
        System.out.println("Been seeing you");;
        return instantiateWeighting(clazz, customModel, lookup);
    }

    private static Class<?> createClazz(CustomModel customModel, EncodedValueLookup lookup) {
        try {
            ClassHelper classHelper = new DefaultClassHelper(lookup);
            return CustomModelCompiler.compile(customModel, lookup, classHelper);
        } catch (Exception e) {
            throw new IllegalArgumentException("Failed to compile custom model", e);
        }
    }

    public static List<String> findVariablesForEncodedValuesString(CustomModel model,
                                                                   NameValidator nameValidator,
                                                                   Function<String, String> variableTransformer,
                                                                   EncodedValueLookup lookup) {
        if (model == null)
            return Collections.emptyList();

        Set<String> variables = new LinkedHashSet<>();
        parseVariablesFromStatements(model.getPriority(), variables, nameValidator, variableTransformer, lookup);
        parseVariablesFromStatements(model.getSpeed(), variables, nameValidator, variableTransformer, lookup);
        return new ArrayList<>(variables);
    }

    private static void parseVariablesFromStatements(List<Statement> statements, Set<String> variables,
                                                     NameValidator validator, Function<String, String> variableTransformer,
                                                     EncodedValueLookup lookup) {
        if (statements == null || lookup == null)
            return;

        ClassHelper classHelper = new DefaultClassHelper(lookup); // Instantiate here

        for (Statement stmt : statements) {
            if (stmt == null) continue;

            if (stmt.isBlock()) {
                parseVariablesFromStatements(stmt.doBlock(), variables, validator, variableTransformer, lookup);
            } else {
                try {
                    variables.addAll(ConditionalExpressionVisitor.findVariables(stmt.condition(), lookup, classHelper));
                    variables.addAll(ValueExpressionVisitor.findVariables(stmt.value(), lookup));
                } catch (Exception e) {
                    throw new IllegalArgumentException("Error parsing statement: " + stmt, e);
                }
            }
        }
    }

    static List<List<Statement>> splitIntoGroup(List<Statement> statements) {
        List<List<Statement>> result = new ArrayList<>();
        List<Statement> group = null;
        for (Statement st : statements) {
            if (IF.equals(st.keyword())) result.add(group = new ArrayList<>());
            if (group == null)
                throw new IllegalArgumentException("Every group must start with an if-statement");
            group.add(st);
        }
        return result;
    }

    private static String getVariableDeclaration(EncodedValueLookup lookup, final String arg) {
        if (arg.equals(OSM_ID_KEY)) {
            return "long " + arg + " = edge.get(" + OSM_ID_KEY + "_enc);\n";
        }
        if (lookup.hasEncodedValue(arg)) {
            EncodedValue enc = lookup.getEncodedValue(arg, EncodedValue.class);
            return getReturnType(enc) + " " + arg + " = (" + getReturnType(enc) + ") (reverse ? " +
                    "edge.getReverse((" + getInterface(enc) + ") this." + arg + "_enc) : " +
                    "edge.get((" + getInterface(enc) + ") this." + arg + "_enc));\n";
        } else if (arg.startsWith(BACKWARD_PREFIX)) {
            final String argSubstr = arg.substring(BACKWARD_PREFIX.length());
            if (lookup.hasEncodedValue(argSubstr)) {
                EncodedValue enc = lookup.getEncodedValue(argSubstr, EncodedValue.class);
                return getReturnType(enc) + " " + arg + " = (" + getReturnType(enc) + ") (reverse ? " +
                        "edge.get((" + getInterface(enc) + ") this." + argSubstr + "_enc) : " +
                        "edge.getReverse((" + getInterface(enc) + ") this." + argSubstr + "_enc));\n";
            } else {
                throw new IllegalArgumentException("Not supported for backward: " + argSubstr);
            }
        } else if (arg.startsWith(IN_AREA_PREFIX)) {
            return "";
        } else {
            throw new IllegalArgumentException("Not supported " + arg);
        }
    }

    private static String getInterface(EncodedValue enc) {
        if (enc instanceof StringEncodedValue) return IntEncodedValue.class.getSimpleName();
        if (enc.getClass().getInterfaces().length == 0) return enc.getClass().getSimpleName();
        return enc.getClass().getInterfaces()[0].getSimpleName();
    }

    private static String getReturnType(EncodedValue encodedValue) {
        // order is important
        if (encodedValue instanceof EnumEncodedValue) {
            Class cl = ((EnumEncodedValue) encodedValue).getEnumType();
            // use getSimpleName for inbuilt EncodedValues and more readability of generated source
            return cl.getPackage().equals(EnumEncodedValue.class.getPackage()) ? cl.getSimpleName() : cl.getName();
        }
        if (encodedValue instanceof StringEncodedValue) return "int"; // we use indexOf
        if (encodedValue instanceof DecimalEncodedValue) return "double";
        if (encodedValue instanceof BooleanEncodedValue) return "boolean";
        if (encodedValue instanceof IntEncodedValue) return "int";
        throw new IllegalArgumentException("Unsupported EncodedValue: " + encodedValue.getClass());
    }

    private static String createClassTemplate(long counter,
                                              Set<String> priorityVariables, Set<String> speedVariables,
                                              EncodedValueLookup lookup, Map<String, JsonFeature> areas) {
        final StringBuilder importSourceCode = new StringBuilder("import com.graphhopper.routing.ev.*;\n");
        importSourceCode.append("import java.util.Map;\n");
        importSourceCode.append("import " + CustomModel.class.getName() + ";\n");
        final StringBuilder classSourceCode = new StringBuilder(100);
        boolean includedAreaImports = false;

        final StringBuilder initSourceCode = new StringBuilder("this.lookup = lookup;\n");
        initSourceCode.append("this.customModel = customModel;\n");
        Set<String> set = new HashSet<>();
        for (String prioVar : priorityVariables)
            set.add(prioVar.startsWith(BACKWARD_PREFIX) ? prioVar.substring(BACKWARD_PREFIX.length()) : prioVar);
        for (String speedVar : speedVariables)
            set.add(speedVar.startsWith(BACKWARD_PREFIX) ? speedVar.substring(BACKWARD_PREFIX.length()) : speedVar);

        for (String arg : set) {
            if (lookup.hasEncodedValue(arg)) {
                EncodedValue enc = lookup.getEncodedValue(arg, EncodedValue.class);
                classSourceCode.append("protected " + getInterface(enc) + " " + arg + "_enc;\n");
                initSourceCode.append("this." + arg + "_enc = (" + getInterface(enc)
                        + ") lookup.getEncodedValue(\"" + arg + "\", EncodedValue.class);\n");
            } else if (arg.startsWith(IN_AREA_PREFIX)) {
                if (!includedAreaImports) {
                    importSourceCode.append("import " + BBox.class.getName() + ";\n");
                    importSourceCode.append("import " + GHUtility.class.getName() + ";\n");
                    importSourceCode.append("import " + PreparedPolygon.class.getName() + ";\n");
                    importSourceCode.append("import " + Polygonal.class.getName() + ";\n");
                    importSourceCode.append("import " + JsonFeature.class.getName() + ";\n");
                    importSourceCode.append("import " + Polygon.class.getName() + ";\n");
                    includedAreaImports = true;
                }

                if (!JsonFeature.isValidId(arg))
                    throw new IllegalArgumentException("Area has invalid name: " + arg);
                String id = arg.substring(IN_AREA_PREFIX.length());
                JsonFeature feature = areas.get(id);
                if (feature == null)
                    throw new IllegalArgumentException("Area '" + id + "' wasn't found");
                if (feature.getGeometry() == null)
                    throw new IllegalArgumentException("Area '" + id + "' does not contain a geometry");
                if (!(feature.getGeometry() instanceof Polygonal))
                    throw new IllegalArgumentException("Currently only type=Polygon is supported for areas but was " + feature.getGeometry().getGeometryType());
                if (feature.getBBox() != null)
                    throw new IllegalArgumentException("Bounding box of area " + id + " must be empty");
                classSourceCode.append("protected " + Polygon.class.getSimpleName() + " " + arg + ";\n");
                initSourceCode.append("JsonFeature feature_" + id + " = (JsonFeature) areas.get(\"" + id + "\");\n");
                initSourceCode.append("this." + arg + " = new Polygon(new PreparedPolygon((Polygonal) feature_" + id + ".getGeometry()));\n");
            } else {
                if (!arg.startsWith(IN_AREA_PREFIX))
                    throw new IllegalArgumentException("Variable not supported: " + arg);
            }
        }

        return ""
                + "package com.graphhopper.routing.weighting.custom;\n"
                + "import " + CustomWeightingHelper.class.getName() + ";\n"
                + "import " + EncodedValueLookup.class.getName() + ";\n"
                + "import " + EdgeIteratorState.class.getName() + ";\n"
                + importSourceCode
                + "\npublic class JaninoCustomWeightingHelperSubclass" + counter + " extends " + CustomWeightingHelper.class.getSimpleName() + " {\n"
                + classSourceCode
                + "   @Override\n"
                + "   public void init(CustomModel customModel, EncodedValueLookup lookup, Map<String, " + JsonFeature.class.getName() + "> areas) {\n"
                + initSourceCode
                + "   }\n\n"
                // we need these placeholder methods so that the hooks in DeepCopier are invoked
                + "   @Override\n"
                + "   public double getPriority(EdgeIteratorState edge, boolean reverse) {\n"
                + "      return 1; //will be overwritten by code injected in DeepCopier\n"
                + "   }\n"
                + "   @Override\n"
                + "   public double getSpeed(EdgeIteratorState edge, boolean reverse) {\n"
                + "      return 1; //will be overwritten by code injected in DeepCopier\n"
                + "   }\n"
                + "}";
    }

    private static class DefaultClassHelper implements ClassHelper {
        private final EncodedValueLookup lookup;

        DefaultClassHelper(EncodedValueLookup lookup) {
            this.lookup = lookup;
        }

        @Override
        public String getClassName(String encodedValueName) {
            EncodedValue enc = lookup.getEncodedValue(encodedValueName, EncodedValue.class);
            if (enc instanceof EnumEncodedValue) {
                return ((EnumEncodedValue<?>) enc).getEnumType().getSimpleName();
            }
            throw new IllegalArgumentException(encodedValueName + " is not an enum encoded value");
        }
    }
}
