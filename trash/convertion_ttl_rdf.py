# brew install jena

# riot --out RDF/XML einstein.ttl > einsten_riot_converted.rdf


# brew install openjdk maven
# git clone https://github.com/rdfhdt/hdt-cpp.git
# cd hdt-cpp/hdt-lib
# mvn install

# java -cp target/hdt-java-1.0.3-jar-with-dependencies.jar org.rdfhdt.hdt.tools.RDF2HDT input.ttl output.hdt






#
 
from rdflib import Graph

# Load the Turtle file
g = Graph()
g.parse("input.ttl", format="turtle")

# Serialize to RDF/XML
g.serialize("output.rdf", format="xml")