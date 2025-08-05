package com.graphhopper.routing.weighting.custom;

import com.graphhopper.routing.ev.EncodedValue;
import com.graphhopper.routing.ev.EncodedValueLookup;
import com.graphhopper.routing.ev.EnumEncodedValue;
import com.graphhopper.util.CustomModel;
import com.graphhopper.json.Statement;
import com.graphhopper.routing.weighting.custom.ValueExpressionVisitor;
import javax.tools.JavaCompiler;
import javax.tools.ToolProvider;
import java.io.*;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.util.*;
import java.util.stream.Collectors;
import freemarker.template.*;
import freemarker.template.Configuration;
import java.io.File;
import java.io.IOException;
import java.net.URL;

public class CustomModelCompiler {
    private static final Configuration cfg = new Configuration(Configuration.VERSION_2_3_31);
    private static final JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
    private static final List<File> tempFiles = new ArrayList<>();

    static {
        try {
            cfg.setClassForTemplateLoading(CustomModelCompiler.class, "/templates");
            cfg.setDefaultEncoding("UTF-8");
        } catch (Exception e) {
            throw new RuntimeException("Could not initialize FreeMarker configuration", e);
        }
    }

    public static Class<?> compile(CustomModel model, EncodedValueLookup lookup, ClassHelper classHelper) throws Exception {
        System.out.println("gotten to this point");
        Map<String, Object> data = prepareTemplateData(model, lookup, classHelper);
        System.out.println("lets talk here");
        String source = processTemplate("CustomWeightingTemplate.java.ftl", data);
        System.out.println("Generated source code:\n" + source);
        String fullClassName = "com.graphhopper.routing.weighting.custom.CustomWeightingHelper_" + model.hashCode();
        File sourceFile = writeTempFile(source, model.hashCode());  // Changed this line
        System.out.println(sourceFile);
        compileJavaFile(sourceFile);
        File rootDir = new File(System.getProperty("java.io.tmpdir"));
        System.out.println("Loading class from: " + rootDir.getAbsolutePath());
        System.out.println("Full class name: " + fullClassName);
        return loadClass(fullClassName, rootDir);
    }

    private static Map<String, Object> prepareTemplateData(CustomModel model, EncodedValueLookup lookup, ClassHelper classHelper) {
        Map<String, Object> data = new HashMap<>();
        data.put("modelHash", model.hashCode());
        data.put("variables", collectVariables(model, lookup));
        data.put("priorityStatements", processStatements(model.getPriority(), lookup, classHelper));
        data.put("speedStatements", processStatements(model.getSpeed(), lookup, classHelper));
        return data;
    }

    private static List<Map<String, Object>> collectVariables(CustomModel model, EncodedValueLookup lookup) {
        Set<String> allVars = new LinkedHashSet<>();
        collectVariablesFromStatements(model.getPriority(), allVars, lookup);
        collectVariablesFromStatements(model.getSpeed(), allVars, lookup);

        return allVars.stream()
                .filter(var -> !var.startsWith("in_")) // Exclude area variables
                .map(var -> {
                    Map<String, Object> varMap = new HashMap<>();
                    varMap.put("name", var);
                    varMap.put("isArea", false);
                    varMap.putAll(createVariableMap(var, lookup));
                    return varMap;
                })
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
    }



    private static void collectVariablesFromStatements(List<Statement> statements, Set<String> variables, EncodedValueLookup lookup) {
        if (statements == null || lookup == null) return;

        // Create the ClassHelper instance
        ClassHelper classHelper = new ClassHelper() {
            @Override
            public String getClassName(String encodedValueName) {
                EncodedValue enc = lookup.getEncodedValue(encodedValueName, EncodedValue.class);
                if (enc instanceof EnumEncodedValue) {
                    return ((EnumEncodedValue<?>) enc).getEnumType().getSimpleName();
                }
                throw new IllegalArgumentException(encodedValueName + " is not an enum encoded value");
            }
        };

        statements.forEach(stmt -> {
            if (stmt.isBlock()) {
                collectVariablesFromStatements(stmt.doBlock(), variables, lookup);
            } else {
                variables.addAll(ValueExpressionVisitor.findVariables(stmt.value(), lookup));
                System.out.println("variables: "+ variables + " stmt.condition() :" + stmt.condition() + " lookup:" + lookup);
                // Pass all 3 arguments now
                variables.addAll(ConditionalExpressionVisitor.findVariables(stmt.condition(), lookup, classHelper));
                System.out.println("sayyyyyyyyy");
            }
        });
    }

        private static Map<String, Object> createVariableMap(String var, EncodedValueLookup lookup) {
            Map<String, Object> map = new HashMap<>();
            if (var.startsWith("in_")) {
                map.put("name", var);
                map.put("type", "Polygon");
                map.put("isArea", true);
                map.put("isEnum", false);
                return map;
            } else if (var.equals("osm_id")) {
                return null;
            } else if (lookup.hasEncodedValue(var)) {
                System.out.println("[DEBUG] Checking encoded value for variable: " + var);
                System.out.println("[DEBUG] Encoded value exists in lookup: " + lookup.hasEncodedValue(var));

                try {
                    System.out.println("[DEBUG] Attempting to get EncodedValue instance for: " + var);
                    EncodedValue ev = lookup.getEncodedValue(var, EncodedValue.class);

                    System.out.println("[DEBUG] Successfully retrieved EncodedValue: " + ev);
                    System.out.println("[DEBUG] EncodedValue class: " + ev.getClass().getName());

                    // Handle EnumEncodedValue specially
                    if (ev instanceof EnumEncodedValue) {
                        System.out.println("[DEBUG] Handling EnumEncodedValue");
                        map.put("name", var);
                        map.put("type", ((EnumEncodedValue<?>) ev).getEnumType().getSimpleName());
                        map.put("isEnum", true);
                        map.put("isArea", false);
                        System.out.println("[DEBUG] Created variable map: " + map);
                        return map;
                    }

                    // For other encoded values, try to get interface
                    Class<?>[] interfaces = ev.getClass().getInterfaces();
                    System.out.println("[DEBUG] Implemented interfaces: " + Arrays.toString(interfaces));

                    if (interfaces.length > 0) {
                        String interfaceName = interfaces[0].getSimpleName();
                        System.out.println("[DEBUG] Using interface: " + interfaceName);

                        map.put("name", var);
                        map.put("type", interfaceName);
                        map.put("isEnum", false);
                        map.put("isArea", false);
                        System.out.println("[DEBUG] Created variable map: " + map);
                        return map;
                    } else {
                        System.out.println("[DEBUG] No interfaces found, using class name directly");
                        map.put("name", var);
                        map.put("type", ev.getClass().getSimpleName());
                        map.put("isEnum", false);
                        map.put("isArea", false);
                        return map;
                    }
                } catch (Exception e) {
                    System.out.println("[DEBUG] Error getting EncodedValue for " + var + ": " + e.getMessage());
                    throw e;
                }
            }
            System.err.println(">>> Unknown variable in custom model: " + var);
            throw new IllegalArgumentException("Unknown variable type: " + var);
        }

    private static List<Map<String, String>> processStatements(List<Statement> statements, EncodedValueLookup lookup, ClassHelper classHelper) {
        if (statements == null) return Collections.emptyList();
        return statements.stream()
                .filter(stmt -> !stmt.isBlock())
                .map(stmt -> {
                    Map<String, String> map = new HashMap<>();
                    map.put("condition", ConditionalExpressionVisitor.toJavaExpression(stmt.condition(), lookup, classHelper));
                    map.put("value", ValueExpressionVisitor.toJavaExpression(stmt.value(), lookup));
                    return map;
                })
                .collect(Collectors.toList());
    }

    private static String processTemplate(String template, Map<String, Object> data) throws IOException, TemplateException {
        try (StringWriter writer = new StringWriter()) {
            cfg.getTemplate(template).process(data, writer);
            return writer.toString();
        }
    }

    private static File writeTempFile(String content, long modelHash) throws IOException {
        String className = "CustomWeightingHelper_" + modelHash;
        String packagePath = "com.graphhopper.routing.weighting.custom".replace('.', File.separatorChar);
        File dir = new File(System.getProperty("java.io.tmpdir"), packagePath);
        if (!dir.exists()) dir.mkdirs();
        File file = new File(dir, className + ".java");
        Files.write(file.toPath(), content.getBytes());
        return file;
    }


    private static void compileJavaFile(File javaFile) throws IOException {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) throw new IllegalStateException("Java compiler not available. Are you running a JDK?");
        int result = compiler.run(null, null, null, javaFile.getPath());
        if (result != 0) {
            throw new RuntimeException("Compilation failed for " + javaFile.getPath());
        }
    }

    private static Class<?> loadClass(String fullClassName, File classDir) throws Exception {
        URLClassLoader classLoader = new URLClassLoader(new URL[]{classDir.toURI().toURL()});
        return classLoader.loadClass(fullClassName);
    }

    public static void cleanup() {
        tempFiles.forEach(f -> {
            try {
                f.delete();
            } catch (Exception e) {
                // ignore
            }
        });
    }
}
