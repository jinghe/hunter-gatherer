all: Search Search-server

INDRI_FOLDER=/path/to/indri
INDRI_INCLUDE=-I $(INDRI_FOLDER)/include -I $(INDRI_FOLDER)/contrib/lemur/include
INDRI_LIB=-L $(INDRI_FOLDER)/obj -L $(INDRI_FOLDER)/contrib/lemur/obj -L $(INDRI_FOLDER)/contrib/xpdf/obj -L $(INDRI_FOLDER)/contrib/antlr/obj


Search: Search.cpp
	g++ -o Search Search.cpp $(INDRI_INCLUDE) $(INDRI_LIB) -lindri -DP_NEEDS_GNU_CXX_NAMESPACE=1 -lpthread -lz 

Search-server: Search-server.cpp
	g++ -o Search-server Search-server.cpp $(INDRI_INCLUDE) $(INDRI_LIB) -lindri -DP_NEEDS_GNU_CXX_NAMESPACE=1 -lpthread -lz

