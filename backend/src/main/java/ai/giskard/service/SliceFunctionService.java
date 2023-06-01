package ai.giskard.service;

import ai.giskard.domain.SliceFunction;
import ai.giskard.repository.ml.SliceFunctionRepository;
import ai.giskard.web.dto.SliceFunctionDTO;
import ai.giskard.web.dto.mapper.GiskardMapper;
import org.springframework.stereotype.Service;

import javax.transaction.Transactional;

@Service

public class SliceFunctionService extends CallableService<SliceFunction, SliceFunctionDTO> {

    private final GiskardMapper giskardMapper;
    private final SliceFunctionRepository sliceFunctionRepository;

    public SliceFunctionService(SliceFunctionRepository sliceFunctionRepository, GiskardMapper giskardMapper) {
        super(sliceFunctionRepository);
        this.giskardMapper = giskardMapper;
        this.sliceFunctionRepository = sliceFunctionRepository;
    }

    @Transactional
    public SliceFunctionDTO save(SliceFunctionDTO sliceFunction) {
        return giskardMapper.toDTO(sliceFunctionRepository.save(sliceFunctionRepository.findById(sliceFunction.getUuid())
            .map(existing -> update(existing, sliceFunction))
            .orElseGet(() -> create(sliceFunction))));
    }


    protected SliceFunction create(SliceFunctionDTO dto) {
        SliceFunction function = giskardMapper.fromDTO(dto);
        function.setVersion(sliceFunctionRepository.countByNameAndModule(function.getName(), function.getModule()) + 1);
        return function;
    }


}
