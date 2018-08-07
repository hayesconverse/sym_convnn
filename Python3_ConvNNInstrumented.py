#This is where we'll be doing our full implementation of a convolutional neural net with symbolic tracking.

import numpy as np;
import matplotlib.pyplot as plt
#import h5py
import json
import time
import tensorflow as tf
#import cPickle
import sys
import PIL.Image
from random import randint
from io import StringIO
from IPython.display import  Image, display

weightMatrix = None
biasMatrix = None
inputMatrix = None
labelMatrix = None
symInput = None

convWeightMatrix = None
convBiasMatrix = None
denseWeightMatrix = None
denseBiasMatrix = None
layerTypeList = []
maxPoolParams = []
activationTypeList = [] 
convParams = []

def read_inputs_from_file(inputFile, height, width, plusPointFive=True):
    global inputMatrix, labelMatrix
    with open(inputFile) as f:
        lines = f.readlines()
        print(len(lines), "examples")
        inputMatrix = np.empty(len(lines),dtype=list)
        labelMatrix = np.zeros(len(lines),dtype=int)
        for l in range(len(lines)):
            k = [float(stringIn) for stringIn in lines[l].split(',')[1:]] #This is to remove the useless 1 at the start of each string. Not sure why that's there.
            inputMatrix[l] = np.zeros((height, width, 1),dtype=float) #we're asuming that everything is 2D for now. The 1 is just to keep numpy happy.
            labelMatrix[l] = lines[l].split(',')[0]
            count = 0
            for i in range(height):
                for j in range(width):
                    if plusPointFive:
                        inputMatrix[l][i][j] = k[count] + 0.5
                    else:
                        inputMatrix[l][i][j] = k[count]
                    count += 1
            #inputMatrix[l] = np.transpose(k) #provides Nx1 output
            
            
def read_weights_from_saved_tf_model(metaFile='tf_models/mnist.meta', ckpoint='./tf_models'):
    global convWeightMatrix, convBiasMatrix, denseWeightMatrix, denseBiasMatrix, layerTypeList, maxPoolParams, activationTypeList, convParams
    graph = tf.Graph()
    with tf.Session() as sess:
        imported_graph = tf.train.import_meta_graph(metaFile)
        imported_graph.restore(sess, tf.train.latest_checkpoint(ckpoint))
        graph = tf.get_default_graph()
        convLayer = 0
        denseLayer = 0
        mostRecentLayer = ""
        conv_layers = [p for p in tf.trainable_variables() if len(p.shape) == 4]
        dense_layers = [p for p in tf.trainable_variables() if len(p.shape) == 2]
        convWeightMatrix = np.empty(len(conv_layers),dtype=list)
        convBiasMatrix = np.empty(len(conv_layers),dtype=list)
        denseWeightMatrix = np.empty(len(dense_layers),dtype=list)
        denseBiasMatrix = np.empty(len(dense_layers),dtype=list)
        for v in tf.trainable_variables():
            if len(v.shape) == 4: #convolutional layer
                layerTypeList.append('conv2d')
                convWeightMatrix[convLayer] = np.zeros(v.shape)
                convWeightMatrix[convLayer] = sess.run(v)
                #print convWeightMatrix[convLayer]
                convParams.append({'strides': [1, 1]})
                mostRecentLayer = "conv"
                layerTypeList.append('activation')
                activationTypeList.append('relu')
                layerTypeList.append('maxpool')
                maxPoolParams.append({'pool_size': [2, 2], 'strides': [2, 2]})
            elif len(v.shape) == 2: #dense layer
                layerTypeList.append('dense')
                denseWeightMatrix[denseLayer] = np.zeros(v.shape)
                denseWeightMatrix[denseLayer] = sess.run(v)
                mostRecentLayer = "dense"
                layerTypeList.append('activation')
                activationTypeList.append('relu')
            elif len(v.shape) == 1: #bias
                if(mostRecentLayer == "conv"):
                    convBiasMatrix[convLayer] = np.zeros(v.shape)
                    convBiasMatrix[convLayer] = sess.run(v)
                    convLayer = convLayer + 1
                elif(mostRecentLayer == "dense"):
                    denseBiasMatrix[denseLayer] = np.zeros(v.shape)
                    denseBiasMatrix[denseLayer] = sess.run(v)
                    denseLayer = denseLayer + 1
                
            print(v.shape)
        if(layerTypeList[-1] == 'activation'):
            layerTypeList[-1] = "" #Removes last activation layer.
        sess.close()
    
def read_weights_from_file(inputFile):
    global weightMatrix, biasMatrix
    with open(inputFile) as f:
        lines = f.readlines()
        numberOfLayers = int(lines[0])
        weightMatrix = np.empty(numberOfLayers, dtype=list)
        biasMatrix = np.empty(numberOfLayers, dtype=list)
        currentLine = 2
        for i in range(numberOfLayers):
            dimensions = lines[currentLine].split(',')
            dimensions = [int(stringDimension) for stringDimension in dimensions]
            #print dimensions
            currentLine += 1
            weights = [float(stringWeight) for stringWeight in lines[currentLine].split(',')]
            #print len(weights)
            count = 0
            weightMatrix[i] = np.zeros((dimensions[0], dimensions[1]), dtype=float)
            for j in range(dimensions[1]):
                for k in range(dimensions[0]):
                    weightMatrix[i][k][j] = weights[count]
                    count += 1
            currentLine += 1
            biases = [float(stringBias) for stringBias in lines[currentLine].split(',')]
            biasMatrix[i] = np.zeros(len(biases))
            biasMatrix[i] = biases
            currentLine += 2

def get_im2col_indices(input_shape, field_height, field_width, padding=1, stride=1):
    #N, C, H, W = input_shape
    #print "N, C, H, W: "+N+" "+C+" "+H+" "+W
    C, H, W = input_shape
    print("C, H, W: ",C,H,W)
    assert (H + 2 * padding - field_height) % stride == 0
    assert (W + 2 * padding - field_height) % stride == 0
    out_height = (H + 2 * padding - field_height) / stride + 1
    out_width = (W + 2 * padding - field_width) / stride + 1
    
    print(out_height, out_width)
    
    i0 = np.repeat(np.arange(field_height), field_width)
    i0 = np.tile(i0, C)
    print(i0)
    i1 = stride * np.repeat(np.arange(out_height), out_width)
    j0 = np.tile(np.arange(field_width), field_height * C)
    j1 = stride * np.tile(np.arange(out_width), out_height)
    i = i0.reshape(-1, 1) + i1.reshape(1, -1)
    j = j0.reshape(-1, 1) + j1.reshape(1, -1)
    
    k = np.repeat(np.arange(C), field_height * field_width).reshape(-1, 1)
    
    return (k, i, j)
    
def im2col_indices(input, section_height, section_width, padding=1, stride=1):
    input_padded = np.pad(input, ((padding, padding),(padding, padding)), mode='constant')
    k, i, j = get_im2col_indices((1,)+input.shape, section_height, section_width, padding, stride)
    print(k, i, j)
    cols = input_padded[:, k, i, j]
    print(cols)
    C = input.shape[1]
    cols = cols.transpose(1, 2, 0).reshape(section_height * section_width * C, -1)
    return cols

def im2col_sliding_strided(A, block_shape, stepsize=1, padding=0):
    m,n,d = A.shape
    A_padded = np.pad(A, ((padding, padding),(padding, padding),(0,0)), mode='constant')
    #print "Im2col input shape:",m, n
    s0, s1, s2 = A_padded.strides   
    #print "Im2col input strides",s0, s1 
    nrows = m-block_shape[0]+1
    ncols = n-block_shape[1]+1
    #print "Im2col output # of rows, cols:",nrows, ncols
    shp = block_shape[0],block_shape[1],nrows,ncols
    #print shp
    strd = s0,s1,s0,s1

    out_view = np.lib.stride_tricks.as_strided(A_padded, shape=shp, strides=strd)
    return out_view.reshape(block_shape[0]*block_shape[1],-1)[:,::stepsize]


def conv_layer_forward(input, filter, b, stride=1, padding=1):
    print("Beginning conv layer")
    #print "Conv: input shape",input.shape
    h_x, w_x, d_x = input.shape #Still assuming one 2D image at a time for now, so we omit the n_x and d_x will be 1 at the start. d_x has to equal d_filter at each iteration
    #print "Conv: filter shape",filter.shape
    n_filters, d_filter, h_filter, w_filter = filter.shape #d_filter should be 1 at start
    h_out = (h_x - h_filter + 2 * padding) / stride + 1
    w_out = (w_x - w_filter + 2 * padding) / stride + 1
    input_col = im2col_sliding_strided(input, (h_filter, w_filter), stride, padding) #im2col_indices(input, filter.shape[0], filter.shape[1], padding=padding, stride=stride)
    print("Input_col shape",input_col.shape)
    print(input_col[4*h_x:5*h_x,:])
    filter_col = filter.reshape(n_filters, -1)
    print("Filter_col shape",filter_col.shape)
    print(filter_col[0,0:h_filter])
    converted_biases = np.array(b).reshape(-1, 1)
    #print "10x1?",converted_biases.shape
    out = np.add(np.dot(filter_col, input_col), converted_biases)
    out = out.reshape(h_out, w_out, n_filters) #(n_filters, h_out, w_out, n_x) if multi-input
    #out = out.transpose(3, 0, 1, 2) #Turns it back to (n_x, n_filters, h_out, w_out), but we don't need that since we don't have multiple inputs
    for i in range(n_filters):
        print("Total for this filter:", out[i,0,0])
    print("output shape",out.shape,"\n")
    return out;
    
def conv_layer_forward_ineff(input, filters, biases, stride=1, padding=1, keras=False):
    print("Beginning conv layer")
    h_x, w_x, d_x = input.shape
    if(keras):
        h_filter, w_filter, d_filter, n_filters = filters.shape #d_x should equal d_filter
    else:
        n_filters, d_filter, h_filter, w_filter = filters.shape
    if(padding == -1):
        padding = (h_filter-1)/2
    print("Before")
    print(padding, h_filter)
    
    padding = np.int64(padding)

    print("After")
    print(padding)

    input_padded = np.pad(input,((padding, padding),(padding, padding),(0,0)),mode='constant')
    print(input.shape, filters.shape)
    h_out = (h_x - h_filter + 2 * padding) / stride + 1
    w_out = (w_x - w_filter + 2 * padding) / stride + 1
    print(h_out, "x", w_out, "out")
    print("Before")
    print(h_out,w_out,n_filters)
    h_out = np.int64(h_out)
    w_out = np.int64(w_out)
    n_filters = np.int64(n_filters)
    print("After")
    print(h_out,w_out,n_filters)
    out = np.zeros((h_out, w_out, n_filters))
    #print "Biases:",biases
    #print input_padded[4,0:w_filter,0]
    #print filters[0,0,0:h_filter,0:w_filter]
    for i in range(n_filters):
        #print "Applying filter", i
        #print "Bias:", biases[i]
        for j in range(h_out):
            for k in range(w_out):
                rowIndex = j*stride
                colIndex = k*stride
                for l in range(d_x):
                    #print filters[i,l].shape
                    #print input_padded[j:j+h_filter,k:k+w_filter,l].shape
                    if(keras):
                        out[j,k,i] = out[j,k,i] + np.sum(np.multiply(filters[:,:,l,i], input_padded[rowIndex:rowIndex+h_filter,colIndex:colIndex+w_filter,l]))
                    else:
                        out[j,k,i] = out[j,k,i] + np.sum(np.multiply(filters[i,l], input_padded[rowIndex:rowIndex+h_filter,colIndex:colIndex+w_filter,l]))
                out[j,k,i] = out[j,k,i] + biases[i]
                #print out[j,k,i]
        #print out[:,:,i]
    print("output shape",out.shape,"\n")
    return out;

def relu_layer_forward(x):
    print("Beginning relu layer")
    relu = lambda x: x * (x > 0).astype(float) #PC = PC ^ x > 0
    return relu(x);
    print("")

def pool_layer_forward(X, size, stride = 1):
    print("Beginning pool layer")
    #print "X shape:",X.shape
    h, w, d = X.shape
    h_out = (h-size)/stride + 1
    w_out = (w-size)/stride + 1
    X_reshaped = X.reshape(h, w, d) #(n*d, 1, h, w)
    X_col = im2col_sliding_strided(X_reshaped, (size, size), stepsize=stride) #im2col_indices(X_reshaped, size, size, padding=0, stride=stride)
    #print "X_col shape:",X_col.shape
    max_idx = np.argmax(X_col, axis=0)
    out = X_col[max_idx, range(max_idx.size)]
    out = out.reshape(h_out, w_out, d) #(h_out, w_out, n, d)
    #out = out.transpose(2, 3, 0, 1)
    print("")
    return out;
    
def pool_layer_forward_ineff(X, size, stride = 1):
    print("Beginning pool layer")
    #print "X shape:",X.shape
    h, w, d = X.shape
    h_out = (h-size)/stride + 1
    w_out = (w-size)/stride + 1
    #X_reshaped = X.reshape(h, w, d)
    h_out = np.int64(h_out)
    w_out = np.int64(w_out)
    d = np.int64(d)
    out = np.zeros((h_out, w_out, d))
    for i in range(h_out):
        for j in range(w_out):
            for k in range(d):
                rowIndex = i*stride
                colIndex = j*stride
                out[i,j,k] = X[rowIndex:rowIndex+size,colIndex:colIndex+size,k].max()
    print("")
    return out
    
def concolic_pool_layer_forward(X, size, stride = 1):
    global symInput
    print("Beginning concolic pool layer")
    h, w, d = X.shape
    h_out = (h-size)/stride + 1
    w_out = (w-size)/stride + 1
    print("Before")
    print(h_out,w_out,d)
    h_out = np.int64(h_out)
    w_out = np.int64(w_out)
    d = np.int64(d)
    print("After")
    print(h_out,w_out,d)
    out = np.zeros((h_out, w_out, d))
    
    for i in range(h_out):
        for j in range(w_out):
            for k in range(d):
                rowIndex = i*stride
                colIndex = j*stride
                #print X[rowIndex:rowIndex+size,colIndex:colIndex+size,k], X[owIndex:rowIndex+size,j:j+size,k].max()
                max_idx = np.argmax(X[rowIndex:rowIndex+size,colIndex:colIndex+size,k])
                max_row = max_idx/size
                max_col = max_idx % size
                #print symInput[i:i+size,j:j+size,k][max_row, max_col].shape
                #symOut[i,j,k] = symInput[rowIndex:rowIndex+size,colIndex:colIndex+size,k][max_row, max_col]
                out[i,j,k] = X[rowIndex:rowIndex+size,colIndex:colIndex+size,k].max()
    #symInput = symOut
    print("")
    return out
    
def concolic_pool_layer_forward_3d(X, size, stride = 1):
    global symInput
    print("Beginning 3D concolic pool layer")
    h, w, d = X.shape
    h_out = (h-size)/stride + 1
    w_out = (w-size)/stride + 1
    out = np.zeros((h_out, w_out, d))
    symOut = np.zeros((h_out, w_out, d, symInput.shape[3], symInput.shape[4], 3))
    for i in range(h_out):
        for j in range(w_out):
            for k in range(d):
                rowIndex = i*stride
                colIndex = j*stride
                #print X[rowIndex:rowIndex+size,colIndex:colIndex+size,k], X[owIndex:rowIndex+size,j:j+size,k].max()
                max_idx = np.argmax(X[rowIndex:rowIndex+size,colIndex:colIndex+size,k])
                max_row = max_idx/size
                max_col = max_idx % size
                #print symInput[rowIndex:rowIndex+size,colIndex:colIndex+size,k][max_row, max_col].shape
                symOut[i,j,k] = symInput[rowIndex:rowIndex+size,colIndex:colIndex+size,k][max_row, max_col]
                out[i,j,k] = X[rowIndex:rowIndex+size,colIndex:colIndex+size,k].max()
    symInput = symOut
    print("")
    return out

def sym_conv_layer_forward(input, filters, b, stride=1, padding=1, keras=False):
    print("Beginning sym conv layer")
    h_prev, w_prev, d_prev, h_x, w_x = input.shape
    if(keras):
        h_filter, w_filter, d_filter, n_filters = filters.shape #d_x should equal d_filter
    else:
        n_filters, d_filter, h_filter, w_filter = filters.shape
    if padding == -1:
        padding = (h_filter - 1)/2
    h_out = (h_prev - h_filter + 2 * padding) / stride + 1
    w_out = (w_prev - w_filter + 2 * padding) / stride + 1
    input_padded = np.pad(input,((padding, padding),(padding, padding),(0,0),(0,0),(0,0)),mode='constant')
    #print "Padded input shape:", input_padded.shape, "filters shape:", filters.shape
    out = np.zeros((h_out, w_out, n_filters, h_x, w_x))
    for i in range(n_filters):
        #print "Applying sym filter", i
        for j in range(h_out):
            for k in range(w_out):
                rowIndex = j*stride
                colIndex = k*stride
                temp = np.zeros((h_x, w_x))
                for l in range(d_prev):
                    #print filters[i,l].shape
                    #print input_padded[j:j+h_filter,k:k+w_filter,l].shape
                    #temp = np.zeros((h_x, w_x))
                    for m in range(h_filter):
                        for n in range(w_filter):
                            if(keras):
                                scaledMatrix = np.multiply(filters[m,n,l,i], input_padded[rowIndex+m,colIndex+n,l])
                            else:
                                scaledMatrix = np.multiply(filters[i,l,m,n], input_padded[rowIndex+m,colIndex+n,l])
                            temp = np.add(temp, scaledMatrix)
                out[j,k,i] = temp
                #out[j,k,i] = np.add(out[j,k,i], b[i])
    
    print("Output shape:", out.shape)
    print("")
    return out
    
def sym_conv_layer_forward_3d(input, filters, b, stride=1, padding=1, keras=False):
    print("Beginning sym conv layer")
    h_prev, w_prev, d_prev, h_x, w_x, d_x = input.shape
    if(keras):
        h_filter, w_filter, d_filter, n_filters = filters.shape #d_x should equal d_filter
    else:
        n_filters, d_filter, h_filter, w_filter = filters.shape
    if padding == -1:
        padding = (h_filter - 1)/2
    h_out = (h_prev - h_filter + 2 * padding) / stride + 1
    w_out = (w_prev - w_filter + 2 * padding) / stride + 1
    input_padded = np.pad(input,((padding, padding),(padding, padding),(0,0),(0,0),(0,0),(0,0)),mode='constant')
    #print "Padded input shape:", input_padded.shape, "filters shape:", filters.shape
    out = np.zeros((h_out, w_out, n_filters, h_x, w_x, d_x))
    for i in range(n_filters):
        #print "Applying sym filter", i
        for j in range(h_out):
            for k in range(w_out):
                rowIndex = j*stride
                colIndex = k*stride
                temp = np.zeros((h_x, w_x, d_x))
                for l in range(d_prev):
                    #print filters[i,l].shape
                    #print input_padded[j:j+h_filter,k:k+w_filter,l].shape
                    #temp = np.zeros((h_x, w_x))
                    for m in range(h_filter):
                        for n in range(w_filter):
                            if(keras):
                                scaledMatrix = np.multiply(filters[m,n,l,i], input_padded[rowIndex+m,colIndex+n,l])
                            else:
                                scaledMatrix = np.multiply(filters[i,l,m,n], input_padded[rowIndex+m,colIndex+n,l])
                            temp = np.add(temp, scaledMatrix)
                out[j,k,i] = temp
                #out[j,k,i] = np.add(out[j,k,i], b[i])
        #plt.figure()
        #plt.imshow(np.sum(np.sum(np.sum(out[:,:,i], axis=0), axis=0),axis=2))
        #plt.show()
    
    print("Output shape:", out.shape)
    print("")
    return out
    
def unused_sym_conv(input, filter, b, stride=1, padding=1):
    #out = np.dot(input, filter)
    #out = out.transpose()
    #print "Conv: input shape",input.shape
    h_x, w_x, d_x = input.shape #Still assuming one 2D image at a time for now, so we omit the n_x and d_x should always be 1
    #print "Conv: filter shape",filter.shape
    n_filters, h_filter, w_filter = filter.shape
    #Want to produce an output of shape (n_filters, h_x, w_x). Using stride=1 and padding=(filter_size-1)/2 will at least guarantee that h_out = h_x and w_out = w_x
    padding = (h_filter-1)/2
    h_out = (h_x - h_filter + 2 * padding) / stride + 1
    w_out = (w_x - w_filter + 2 * padding) / stride + 1
    input_col = im2col_sliding_strided(input, (h_filter, w_filter), stride, padding) #im2col(input, filter.shape[0], filter.shape[1], padding=padding, stride=stride)
    #print "Input_col shape",input_col.shape
    filter_col = filter.reshape(n_filters, -1)
    #print "Filter_col shape",filter_col.shape
    #converted_biases = np.array(b).reshape(-1, 1)
    #out = np.add(np.dot(filter_col, input_col), converted_biases)
    out = out.reshape(n_filters, h_out, w_out) #(n_filters, h_out, w_out, n_x) if multi-input
    #out = out.transpose(3, 0, 1, 2) #Turns it back to (n_x, n_filters, h_out, w_out), but we don't need that since we don't have multiple inputs
    #print "output shape",out.shape
    return out;
    
def init_symInput(inputHeight, inputWidth):
    global symInput
    symInput = np.zeros((inputHeight, inputWidth, 1, inputHeight, inputWidth))
    for i in range(inputHeight):
        for j in range(inputWidth):
            symInput[i,j,0,i,j] = 1
            
def init_3d_symInput(inputHeight, inputWidth):
    global symInput
    symInput = np.zeros((inputHeight, inputWidth, 3, inputHeight, inputWidth, 3))
    for i in range(inputHeight):
        for j in range(inputWidth):
            for k in range(3):
                symInput[i,j,k,i,j,k] = 1

def init(inputFile, weightFile, inputHeight, inputWidth, plusPointFive=True):
    global symInput
    read_inputs_from_file(inputFile, inputHeight, inputWidth, plusPointFive)
    read_weights_from_file(weightFile)
    init_symInput(inputHeight, inputWidth)
    
def classify(processedArray):
    maxValue = 0
    maxIndex = -1
    for i in range(len(processedArray)):
        print("Class",i,"confidence",processedArray[i,0,0])
        if(processedArray[i,0,0] > maxValue):
            maxValue = processedArray[i,0,0]
            maxIndex = i
    print("MaxIndex:",maxIndex)
    
def classify_ineff(processedArray):
    maxValue = -1000.0
    maxIndex = -1
    for i in range(processedArray.shape[2]):
        print("Class",i,"confidence",processedArray[0,0,i])
        if(processedArray[0,0,i] > maxValue):
            maxValue = processedArray[0,0,i]
            maxIndex = i
    print("MaxIndex:",maxIndex)
    #print symInput[0,0,maxIndex]
    return maxIndex
  

def reshape_fc_weight_matrix_keras(fcWeights, proper_shape):
    total_height, n_filters = fcWeights.shape
    proper_height, proper_width, proper_depth = proper_shape
    return fcWeights.reshape((proper_height, proper_width, proper_depth, n_filters))


def reshape_fc_weight_matrix(fcWeights, proper_shape):
    total_height, n_filters = fcWeights.shape
    proper_height, proper_width, proper_depth = proper_shape
    temp = np.zeros((n_filters, proper_depth, proper_height, proper_width))
    
    for i in range(n_filters):
        for j in range(proper_depth):
            for k in range(proper_height):
                for l in range(proper_width):
                    index = k*proper_width + l + j
                    temp[i,j,k,l] = fcWeights[index,i]
    return temp

def inspect_sym_input(inputImage):
    for i in range(symInput.shape[2]):
        thing = np.zeros((symInput.shape[3],symInput.shape[4]))
        for j in range(symInput.shape[0]):
            for k in range(symInput.shape[1]):
                thing = np.add(thing, symInput[j,k,i])
        plt.figure()
        plt.imshow(normalize_to_255(np.multiply(thing, inputImage[:,:,0])))
        plt.title("Sym input at node %d"%i)
        plt.show()
        
def inspect_3d_sym_input():
    for i in range(symInput.shape[2]):
        thing = np.zeros((symInput.shape[3],symInput.shape[4],symInput.shape[5]))
        for j in range(symInput.shape[0]):
            for k in range(symInput.shape[1]):
                thing = np.add(thing, symInput[j,k,i])
        for l in range(symInput.shape[5]):
            plt.figure()
            plt.imshow(thing[:,:,l])
            plt.title("Sym input at node %d, color %d" % (i, l))
            plt.show()
        
def inspect_intermediate_output(temp):
    for i in range (temp.shape[2]):
        thing = np.zeros((temp.shape[0],temp.shape[1]))
        for j in range(temp.shape[0]):
            for k in range(temp.shape[1]):
                thing = np.add(thing, temp[:,:,i])
        plt.figure()
        plt.imshow(thing)
        plt.show()
        
def get_top_pixels(x, percent):
    temp = x.flatten()
    top_values = np.unique(temp)[-int(len(np.unique(temp)) * percent):]
    print("Returning", int(len(np.unique(temp)) * percent), "pixels")
    for i in range(len(temp)):
        if temp[i] not in top_values:
            temp[i] = 0
    return temp.reshape(x.shape)
    
def get_above_average_pixels(x):
    temp = x.flatten()
    average = np.average(np.unique(x.flatten()))
    for i in range(len(temp)):
        if not (temp[i] >= average):
            temp[i] = 0
    return temp.reshape(x.shape)
    
def get_most_different_pixels(x, y):
    xTemp = x.flatten()
    yTemp = y.flatten()
    temp = np.zeros(xTemp.shape)
    for i in range(len(xTemp)):
        temp[i] = abs(xTemp[i] - yTemp[i])
    temp = temp.reshape(x.shape)
    return temp
    
def compare_pixel_ranks(x, y, tolerance=0):
    temp1 = x.flatten()
    temp2 = y.flatten()
    top_indices_1 = np.argsort(temp1)
    top_indices_2 = np.argsort(temp2)
    equal_locations = 0
    for i in range(len(top_indices_1)):
        #if top_indices_1[i] <= top_indices_2[i]+tolerance and top_indices_1[i] >= top_indices_2[i]-tolerance:
        if abs(top_indices_1[i] - top_indices_2[i]) <= tolerance:
            equal_locations += 1
    print("Ranks are equal at", equal_locations, "spots")
    return equal_locations
    
def image_based_on_pixel_ranks(x):
    temp = x.flatten()
    sortIndices = temp.argsort()
    ranks = np.empty_like(sortIndices)
    ranks[sortIndices] = np.arange(len(temp))
    return ranks.reshape(x.shape)
    
def write_pixel_ranks_to_file(x, filename):
    temp = x.flatten()
    sortIndices = temp.argsort()
    ranks = np.empty_like(sortIndices)
    ranks[sortIndices] = np.arange(len(temp))
    ranks = ranks.reshape(x.shape)
    write_image_to_file(ranks, filename)
    
            
def write_image_to_file(x, filename):
    with open(filename, "w") as f:
        if len(x.shape) == 2:
            for i in range(x.shape[0]):
                for j in range(x.shape[1]):
                    f.write("%f\t" % x[i,j])
                f.write("\n")
        else:
            for k in range(x.shape[2]):
                for i in range(x.shape[0]):
                    for j in range(x.shape[1]):
                        f.write("%f\t" % x[i,j,k])
                    f.write("\n")
                f.write("\n")
            
def write_image_to_file_scientific(x, filename):
    with open(filename, "w") as f:
        for i in range(x.shape[0]):
            for j in range(x.shape[1]):
                f.write("%E\t" % x[i,j])
            f.write("\n")
    
def normalize_to_255(x):
    temp = x.flatten()
    maximum = np.amax(temp)
    minimum = np.amin(temp)
    norm = np.multiply(np.array([(i - minimum) / (maximum - minimum) for i in temp]), 255)
    return norm.reshape(x.shape)
    
def normalize_to_1(x):
    temp = x.flatten()
    maximum = np.amax(temp)
    minimum = np.amin(temp)
    norm = np.multiply(np.array([(i - minimum) / (maximum - minimum) for i in temp]), 1)
    return norm.reshape(x.shape)
    
def gray_scale(img):
    img = np.average(img, axis=2)
    return np.transpose([img, img, img], axes=[1,2,0])
  
def pil_img(a):
    a = np.uint8(a)
    return PIL.Image.fromarray(a)
  
def show_img(img, fmt='jpeg'):
    img.show()
  
def visualize_attrs_windowing(img, attrs, ptile=99):
    attrs = gray_scale(attrs)
    attrs = abs(attrs)
    attrs = np.clip(attrs/np.percentile(attrs, ptile), 0,1)
    vis = img*attrs
    show_img(pil_img(vis))
    return pil_img(vis)
    
def do_all_layers_keras(inputNumber, outDir):
    global symInput, convWeightMatrix, denseWeightMatrix
    temp = inputMatrix[inputNumber]
    convIndex = 0
    denseIndex = 0
    poolIndex = 0
    activationIndex = 0
    reluCounter = 0
    for layerType in layerTypeList:
        if layerType.lower().startswith("conv"):
            #print convWeightMatrix[convIndex], convBiasMatrix[convIndex], convParams[convIndex]['strides'][0]
            # When using the keras file: padding of zero. When using mnist_deep: -1.
            temp = conv_layer_forward_ineff(temp, convWeightMatrix[convIndex], convBiasMatrix[convIndex], convParams[convIndex]['strides'][0], -1, keras=True)
            #symInput = sym_conv_layer_forward(symInput, convWeightMatrix[convIndex], convBiasMatrix[convIndex], convParams[convIndex]['strides'][0], 0, keras=True)
            convIndex = convIndex + 1
            #inspect_intermediate_output(temp)
            #inspect_sym_input()
        elif layerType.lower().startswith("activation"):
            activationType = activationTypeList[activationIndex].lower()
            if activationType == 'relu':
                np.set_printoptions(threshold=np.nan)
                temp = relu_layer_forward(temp)
                if reluCounter == 0:
                    print("ReluCounter=0")
                    a,b,c = temp.shape
                    print(type(temp))
                    bitstr = list()
                    for i1 in range(a):
                        for i2 in range(b):
                            for i3 in range(c):
                                val = temp[i1,i2,i3]
                                val = 1 if val > 0 else 0
                                bitstr.append(val)
                    reluCounter += 1
                    with open('bitstr.txt','w') as f:
                        s = str(bitstr)
                        f.write(s[1:-1]+'\n')
		#TO DO Export activations for the first layer
                #for i in range(temp.shape[0]):
                 #   for j in range(temp.shape[1]):
                  #      print temp[i, j]'''
                #for i in range(temp.shape[2]):
                 #   print temp[:, :, i]'''
                #symInput = relu_layer_forward(symInput)
            activationIndex = activationIndex + 1
        elif layerType.lower().startswith("maxpool"):
            #inspect_intermediate_output(temp)
            #inspect_sym_input()
            #temp = pool_layer_forward_ineff(temp, maxPoolParams[poolIndex]['pool_size'][0], maxPoolParams[poolIndex]['strides'][0])
            temp = concolic_pool_layer_forward(temp, maxPoolParams[poolIndex]['pool_size'][0], maxPoolParams[poolIndex]['strides'][0])
            #inspect_intermediate_output(temp)
            #inspect_sym_input()
            poolIndex = poolIndex + 1 
        elif layerType.lower().startswith("flatten"):
            pass
        elif layerType.lower().startswith("dense"):
            tempWeightMatrix = reshape_fc_weight_matrix_keras(denseWeightMatrix[denseIndex], temp.shape)
            temp = conv_layer_forward_ineff(temp, tempWeightMatrix, denseBiasMatrix[denseIndex], 1, 0, keras=True)
            #symInput = sym_conv_layer_forward(symInput, tempWeightMatrix, denseBiasMatrix[denseIndex], 1, 0, keras=True)
            #inspect_sym_input(inputMatrix[inputNumber])
            denseIndex = denseIndex + 1
    maxIndex = classify_ineff(temp);
    #Coeffs, coeffs*input
    if maxIndex != labelMatrix[inputNumber]:
        print("Error, correct label is", labelMatrix[inputNumber])
    return maxIndex
    
    

weightsFile = "./mnist_3A_layer.txt"
inputsFile = "./mnist_train.csv"
exampleInputsFile = "./example_10.txt"
cifarInputsFile = "./cifar-10-batches-py/test_batch"
h5File = "./mnist_complicated.h5"
cifarH5File = "./cifar10_complicated.h5"
cifarModelFile = "./cifar_model/model.json"
modelFile = "./model.json"
metaFile = "./tf_models/mnist.meta"
altMetaFile = './tf_models/gradients_testing_20000.meta'
noDropoutMetaFile = "./tf_models/mnist_no_dropout.meta"
noPoolingMetaFile = "./tf_models/mnist_no_pooling.meta"
reluMetaFile = "./tf_models_relu/mnist_relu_network.meta"
reluFrameworkMetaFile = "./tf_models_relu_framework/mnist_relu_framework.meta"
alexMetaFile ="./tf_models_alex/mnist_alex.meta"
gradientsTestingMetaFile = './tf.models/gradients_testing.meta'
checkpoint = "./tf_models"
reluCheckpoint = "./tf_models_relu"
reluFrameworkCheckpoint = "./tf_models_relu_framework"
alexCheckpoint = "./tf_models_alex"
gradientRanksFile = "./result_images/gradient_test/gradient_test_pre_softmax_ranks_0.txt"
experimentRanksFile = "./result_images/mnist_deep/pixel_ranks/mnist_deep_sym_coeffs_ranks_0.txt"
inputIndex = 3

#read_inputs_from_file(exampleInputsFile, 28, 28, True)
#exampleInputMatrix = np.multiply(255, inputMatrix)
#exampleInputMatrix = inputMatrix
#labelMatrix = np.arange(10)

#do_experiment(inputsFile, weightsFile, metaFile, 50, "./out.txt")

#Use this one for differential analysis of mnist_deep and tf_relu networks. Gradient analysis of mnist_deep (and tf_relu, if you really need it) is done in test.py/tf_testing_3()
#find_closest_input_with_different_label(inputsFile, reluMetaFile, inputIndex, ckpoint=reluCheckpoint)

#Use these for differential and gradient analysis of mnist_alex network.
#generate_alex_net_mnist_differential_attributions(inputsFile, inputIndex)
#generate_alex_net_mnist_gradients()

#Use these for differential and gradient analysis of our original relu network.
#generate_relu_differential_attributions(inputsFile, inputIndex)
#generate_relu_gradients_and_integrated_grads(inputIndex)

#random_distances_experiment(inputsFile, metaFile, inputIndex=0)
#sufficient_distance_experiment(inputsFile, metaFile, inputIndex=9)
#get_percentage_same_ranks(gradientRanksFile, experimentRanksFile)

#Get coefficients for cifar-10 images using alexnet. 
#read_cifar_inputs(cifarInputsFile)
#read_weights_from_h5_file(cifarH5File)
#parse_architecture_and_hyperparams(cifarModelFile)
#init_3d_symInput(32, 32)
#kerasResult = do_all_layers_keras_3d(inputIndex, 'cifar_alex')

#generate_alex_net_cifar_differential_attributions(cifarInputsFile, inputIndex)

#for i in range(10):
#generate_alex_net_cifar_gradients(i)

#Get coefficients for mnist images using (non-tf) relu network.
#init(exampleInputsFile, weightsFile, 28, 28, True)
#do_all_layers(inputIndex, 0, 1)

#Get coefficients for mnist images using mnist_deep networks. Read weights from correct meta file to choose between them. 
read_weights_from_saved_tf_model(metaFile, checkpoint)
#Parse mnist_train.csv file
init(inputsFile, weightsFile, 28, 28)
inputNumber = 0
kerasResult = do_all_layers_keras(inputNumber, 'convnn_relu_exp')

#Get coefficients for mnist images using alexnet.
#read_weights_from_h5_file(h5File)
#parse_architecture_and_hyperparams(modelFile)
#init(exampleInputsFile, weightsFile, 28, 28, True)
#kerasResult = do_all_layers_keras(inputIndex, 'mnist_alex')

#Prints distances between pairs of rank files. Can't use the loop for differential, since the names aren't consistent (0 vs 6, 1 vs 7, etc.)
#total = 0
#for i in range(len(exampleInputMatrix)):
    #d=get_rank_distance_from_files(('./result_images/inputs/Pixel_ranks/mnist_input_image_ranks_%d.txt' % inputIndex), ('./result_images/differential_attributions/mnist_alex/difference_times_input/Pixel_ranks/%d_vs_1_different_coeffs_times_in_ranks.txt'%inputIndex))
    #print d
    #total += d
#print total/10
