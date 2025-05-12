import struct
import yaml
import os
import argparse
from deepmerge import always_merger

def change_extension(filepath, option_1, option_2 ):
    base, extension = os.path.splitext(filepath)
    if extension.lstrip('.') == option_2:
        extension = option_1
    else:
        extension = option_1
    return  f"{base}.{extension.lstrip('.')}", extension

def unpack_satres_value(valueType,f, key = '' ):
        value = None        

        if valueType not in [1,2,5,6,10,38]:
            print( f'ERROR enknown valuetype : {key} = {valueType}') 
            exit   

        if valueType == 1: #boolean            
            chunk = f.read(2)
            value = struct.unpack('>b', chunk[1:])[0]
        if valueType == 2: #byte            
            chunk = f.read(5)            
            value = struct.unpack('>i', chunk[1:])[0]
        if valueType == 5: #long?
            chunk = f.read(9)
            value = struct.unpack('>q', chunk[1:])[0]
        if valueType == 6: #?
            chunk = f.read(9)
            value = struct.unpack('>d', chunk[1:])[0]
        if valueType == 10:
            chunk = f.read(5)
            chunk_len = struct.unpack('>i', chunk[1:])[0]
            if chunk_len > 0 and chunk_len != 31525858816557311:
                chunk = f.read(chunk_len)             
                value = chunk.decode('utf-16BE', errors='ignore')
            else:
                value = ''
        if valueType == 38: # float
            chunk = f.read(9)
            value = struct.unpack('>d', chunk[1:])[0] 
        return value

def pack_satres_type(type, val):

    if type == 1:
        return struct.pack('>ibb',type ,0, val)
    if type == 2:
        return struct.pack('>ibi',type ,0,val)
    if type == 5: 
        return struct.pack('>ibq',type ,0, val)
    if type == 6: #float
        return struct.pack('>ibd',type ,0, val)
    if type == 10:
        bytes = val.encode('utf-16BE')
        b_len = len(bytes)
        return struct.pack(f'>ibi{b_len}s',type ,0,b_len,bytes)
    if type == 38:
        return struct.pack('>ibd',type ,0, val)


def traverse_dict_gen(d, path=[]):
    if isinstance(d, dict):
        for k, v in d.items():
            if ( k == '$'):
                bytes = '/'.join(path).encode('utf-16BE')
                str_len = len(bytes)
                yield ( struct.pack(f'>l{str_len}s',str_len,bytes),pack_satres_type(v['Type'],v['Value']))        
            else:
                yield from traverse_dict_gen(v, path + [k])
    else:       
        #str_len = 0
        yield ( ) #struct.pack(f'>l{str_len}s',str_len,bytes),packType(d['Type'],d['Value']))


def write_satres_file(satres_file, yaml):
    entries = list(traverse_dict_gen(yaml))
    with open(satres_file, 'wb') as file:
        file.write(struct.pack('>l',len(entries)))
        for path in entries:
            file.write(path[0])
            file.write(path[1])    

def read_satres_file(filepath):
    root = {}

    with open(filepath, 'rb') as f:
        chunk = f.read(4)         
        pair_count = int.from_bytes(chunk, byteorder='big')
        
        while chunk := f.read(4):
            chunk_len = int.from_bytes(chunk, byteorder='big')

            chunk = f.read(chunk_len)        
            key = chunk.decode( 'utf-16BE', errors="ignore")
        
            spot = root

            for part in key.split('/'):
                if spot.get(part) == None:
                    spot.update({ part: {} })
                spot = spot.get(part)
            
            chunk = f.read(4)
            valueType = int.from_bytes(chunk, byteorder='big')    

            value = unpack_satres_value(valueType, f, key)
                    
            spot.update({'$': {'Type': valueType, 'Value': value} })
    
    return root

def write_yaml(file_name, root):
    with open(file_name, 'w') as file:
        yaml.dump(root, file, default_flow_style=False)

def flat_map_gen(d, path=[]):
    if isinstance(d, dict):
        for k, v in d.items():
            if ( k == '$'):                
                yield [  '/'.join(path) , v["Type"], v['Value'] ]
            else:
                yield from flat_map_gen(v, path + [k])
    else:
       yield (  path + [d] , d )

def print_flatmap( dict ):
    for path in (flat_map_gen(dict)):
        print(path)

def read_resource_file( file_path ):
    if os.path.splitext(file_path)[1] == '.satres':
        return read_satres_file(file_path)
    else:
        with open(file_path, "r") as f1:
            return yaml.safe_load(f1)    

parser = argparse.ArgumentParser(description="Process an input filename.")
parser.add_argument("source_file", type=str, help="The input satres or yaml file")

parser.add_argument("-l", "--list", help="Print list of kays and their values", action="store_true")

parser.add_argument("-m", "--merge", help="Satres or Yaml file to be merged", action = 'store')

parser.add_argument("-o", "--output", help="Name of output file, if value or format is not provided will be opposite of input", action = 'store', nargs = '?')

parser.add_argument("-f", "--format", help="Format of output file", choices=['yaml', 'satres'],  action = 'store' )

args = parser.parse_args()

# print(f"Input filename: {args.source_file}")

root = read_resource_file(args.source_file )

if args.list:
    print_flatmap(root)

if args.merge:
    merge = read_resource_file(args.merge )
    root = always_merger.merge(root, merge)

if args.output != True:          
    if args.format == None and args.output == None:
        args.output, args.format = change_extension(args.source_file, 'yaml', 'satres')    

    if args.output == None:                
        args.output, args.format = change_extension(args.source_file, args.format or 'yaml', args.format or 'satres')    

    if args.format == None:
        args.format = os.path.splitext(args.output)[1].lstrip('.')

    if args.format == 'yaml':
        write_yaml(args.output, root)

    if args.format == 'satres':
        write_satres_file(args.output, root)

else:
    print(yaml.dump(root, default_flow_style=False))



       