### This is the code to produce the image displayed above ###

#import pylab
import numpy
#from IPython.core.pylabtools import figsize

def smoothList(list, strippedXs=False, degree=10):
    if strippedXs == True: return Xs[0:-(len(list) - (len(list) - degree + 1))]
    smoothed = [0] * (len(list) - degree + 1)
    for i in range(len(smoothed)):
        smoothed[i] = sum(list[i:i + degree]) / float(degree)

    return smoothed


def smoothListTriangle(list, strippedXs=False, degree=5):
    weight = []
    window = degree * 2 - 1
    smoothed = [0.0] * (len(list) - window)
    for x in range(1, 2 * degree): weight.append(degree - abs(degree - x))
    w = numpy.array(weight)
    for i in range(len(smoothed)):
        smoothed[i] = sum(numpy.array(list[i:i + window]) * w) / float(sum(w))
    return smoothed


def smoothListGaussian(list, strippedXs=False, degree=5):
    window = degree * 2 - 1

    weight = numpy.array([1.0] * window)

    weightGauss = []

    for i in range(window):
        i = i - degree + 1

        frac = i / float(window)

        gauss = 1 / (numpy.exp((4 * (frac)) ** 2))

        weightGauss.append(gauss)

    weight = numpy.array(weightGauss) * weight

    smoothed = [0.0] * (len(list) - window)

    for i in range(len(smoothed)):
        smoothed[i] = sum(numpy.array(list[i:i + window]) * weight) / sum(weight)

    return smoothed


# def plot1d(lists):
#     pylab.figure(figsize=(1000 / 80, 1000 / 80))
#     pylab.suptitle('1D Data Smoothing', fontsize=16)
#
#     for i, l in enumerate(lists):
#         pylab.subplot(len(lists), 1, i + 1)
#         p1 = pylab.plot(l, ".k")
#         p1 = pylab.plot(l, "-k")
#
#         # a=pylab.axis()
#         if i == 0:
#             a = pylab.axis()  # [a[0],a[1],-.1,1.1])
#         else:
#             pylab.axis(a)
#         pylab.text(0, 0.0001, "data {}".format(i), fontsize=12)
#     pylab.show()
#     # pylab.waitforbuttonpress()
#     pylab.close()


if __name__ == "__main__":
    d = []
    for i in range(1000):
        d.append(0)
    for i in range(300, 700):
        d[i] = .5
    for i in range(500, 600):
        d[i] = 1
    # print(d)
    #plot1d([d, smoothList(d, 100), smoothListGaussian(d, 200)])
