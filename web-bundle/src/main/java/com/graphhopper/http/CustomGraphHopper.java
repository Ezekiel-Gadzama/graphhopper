package com.graphhopper.http;
import com.graphhopper.GraphHopper;
import com.graphhopper.routing.ev.*;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.util.OSMParsers;
import com.graphhopper.routing.util.parsers.OSMIDTagParser;
import com.graphhopper.util.PMap;
import java.util.List;
import java.util.Map;

public class CustomGraphHopper extends GraphHopper {

    @Override
    protected EncodingManager buildEncodingManager(
            Map<String, PMap> encodedValuesWithProps,
            Map<String, ImportUnit> activeImportUnits,
            Map<String, List<String>> restrictionVehicleTypesByProfile) {

        encodedValuesWithProps.putIfAbsent(OSMIDTagParser.KEY, new PMap());
        EncodingManager.Builder emBuilder = new EncodingManager.Builder();

        for (EncodedValue ev : super.buildEncodingManager(
                encodedValuesWithProps, activeImportUnits, restrictionVehicleTypesByProfile).getEncodedValues()) {
            emBuilder.add(ev);
        }

        // Fixed: Use SimpleIntEncodedValue instead of EncodedValueFactory
        emBuilder.add(new IntEncodedValueImpl(OSMIDTagParser.KEY, 32, false));
        return emBuilder.build();
    }

    @Override
    protected OSMParsers buildOSMParsers(
            Map<String, PMap> encodedValuesWithProps,
            Map<String, ImportUnit> activeImportUnits,
            Map<String, List<String>> restrictionVehicleTypesByProfile,
            List<String> ignoredHighways) {

        OSMParsers osmParsers = super.buildOSMParsers(
                encodedValuesWithProps, activeImportUnits, restrictionVehicleTypesByProfile, ignoredHighways);
        osmParsers.addWayTagParser(new OSMIDTagParser(getEncodingManager()));
        return osmParsers;
    }
}
